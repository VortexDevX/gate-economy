import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.admin import AdminPlayer
from app.core.deps import DBSession
from app.models.event import Event, EventType
from app.models.leaderboard import PlayerNetWorth, Season, SeasonResult, SeasonStatus
from app.models.ledger import AccountEntityType, EntryType, LedgerEntry
from app.models.player import Player
from app.models.tick import Tick
from app.schemas.admin import (
    AdminLedgerEntry,
    ConservationAuditResponse,
    EventTriggerRequest,
    EventTriggerResponse,
    ParameterResponse,
    ParameterUpdate,
    SeasonActionRequest,
    SeasonActionResponse,
    SimulationControlResponse,
    TreasuryResponse,
    TreasuryLedgerEntry,
)
from app.services.admin import (
    PAUSE_KEY,
    get_treasury_info,
    list_parameters,
    run_conservation_audit,
    update_parameter,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Simulation Control ──


@router.post("/simulation/pause", response_model=SimulationControlResponse)
async def pause_simulation(admin: AdminPlayer):
    from redis.asyncio import Redis as R
    from app.config import settings as s
    r = R.from_url(s.redis_url, decode_responses=True)
    try:
        await r.set(PAUSE_KEY, "1")
    finally:
        await r.aclose()
    logger.info("simulation_paused", by=str(admin.id))
    return SimulationControlResponse(status="paused", message="Simulation paused")


@router.post("/simulation/resume", response_model=SimulationControlResponse)
async def resume_simulation(admin: AdminPlayer):
    from redis.asyncio import Redis as R
    from app.config import settings as s
    r = R.from_url(s.redis_url, decode_responses=True)
    try:
        await r.delete(PAUSE_KEY)
    finally:
        await r.aclose()
    logger.info("simulation_resumed", by=str(admin.id))
    return SimulationControlResponse(status="running", message="Simulation resumed")


# ── Parameters ──


@router.get("/parameters", response_model=list[ParameterResponse])
async def get_parameters(admin: AdminPlayer, db: DBSession):
    params = await list_parameters(db)
    return params


@router.patch("/parameters/{key}", response_model=ParameterResponse)
async def patch_parameter(
    key: str,
    body: ParameterUpdate,
    admin: AdminPlayer,
    db: DBSession,
):
    try:
        param = await update_parameter(db, key, body.value, admin.id)
        await db.commit()
        return param
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Events ──


@router.post("/events/trigger", response_model=EventTriggerResponse)
async def trigger_event(
    body: EventTriggerRequest,
    admin: AdminPlayer,
    db: DBSession,
):
    try:
        event_type = EventType(body.event_type)
    except ValueError:
        valid = [e.value for e in EventType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Valid: {valid}",
        )

    result = await db.execute(
        select(Tick.id).order_by(Tick.tick_number.desc()).limit(1)
    )
    tick_id = result.scalar_one_or_none() or 0

    event = Event(
        event_type=event_type,
        tick_id=tick_id,
        payload={"triggered_by": str(admin.id), "admin_triggered": True},
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return EventTriggerResponse(
        event_id=event.id,
        event_type=event_type.value,
        tick_id=tick_id if tick_id > 0 else None,
        message=f"Event {event_type.value} triggered by admin",
    )


# ── Treasury ──


@router.get("/treasury", response_model=TreasuryResponse)
async def get_treasury(admin: AdminPlayer, db: DBSession):
    info = await get_treasury_info(db)
    return TreasuryResponse(
        treasury_id=info["treasury_id"],
        balance_micro=info["balance_micro"],
        recent_entries=[
            TreasuryLedgerEntry.model_validate(e) for e in info["recent_entries"]
        ],
    )


# ── Conservation Audit ──


@router.get("/audit/conservation", response_model=ConservationAuditResponse)
async def audit_conservation(admin: AdminPlayer, db: DBSession):
    result = await run_conservation_audit(db)
    return ConservationAuditResponse(**result)


# ── Ledger ──


@router.get("/ledger", response_model=list[AdminLedgerEntry])
async def get_ledger(
    admin: AdminPlayer,
    db: DBSession,
    entry_type: str | None = Query(None),
    player_id: UUID | None = Query(None),
    tick_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(LedgerEntry)

    if entry_type is not None:
        try:
            et = EntryType(entry_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid entry_type: {entry_type}"
            )
        query = query.where(LedgerEntry.entry_type == et)

    if player_id is not None:
        query = query.where(
            (
                (LedgerEntry.debit_type == AccountEntityType.PLAYER)
                & (LedgerEntry.debit_id == player_id)
            )
            | (
                (LedgerEntry.credit_type == AccountEntityType.PLAYER)
                & (LedgerEntry.credit_id == player_id)
            )
        )

    if tick_id is not None:
        query = query.where(LedgerEntry.tick_id == tick_id)

    query = query.order_by(LedgerEntry.id.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


# ── Seasons ──


@router.post("/seasons", response_model=SeasonActionResponse)
async def manage_season(
    body: SeasonActionRequest,
    admin: AdminPlayer,
    db: DBSession,
):
    if body.action == "create":
        # Check no active season exists
        result = await db.execute(
            select(Season).where(Season.status == SeasonStatus.ACTIVE)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409, detail="Active season already exists"
            )

        # Current tick
        result = await db.execute(
            select(Tick.tick_number).order_by(Tick.tick_number.desc()).limit(1)
        )
        current_tick = result.scalar_one_or_none() or 0

        # Next season number
        result = await db.execute(
            select(func.coalesce(func.max(Season.season_number), 0))
        )
        next_number = result.scalar_one() + 1

        season = Season(
            season_number=next_number,
            start_tick=current_tick + 1,
            status=SeasonStatus.ACTIVE,
        )
        db.add(season)
        await db.commit()
        await db.refresh(season)

        return SeasonActionResponse(
            season_id=season.id,
            season_number=season.season_number,
            action="create",
            message=f"Season {season.season_number} created, starts at tick {season.start_tick}",
        )

    # action == "end"
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.ACTIVE)
    )
    season = result.scalar_one_or_none()
    if season is None:
        raise HTTPException(status_code=404, detail="No active season")

    result = await db.execute(
        select(Tick.tick_number).order_by(Tick.tick_number.desc()).limit(1)
    )
    current_tick = result.scalar_one_or_none() or 0

    season.end_tick = current_tick
    season.status = SeasonStatus.COMPLETED

    # Generate results from current net worth data
    result = await db.execute(
        select(PlayerNetWorth)
        .join(Player, Player.id == PlayerNetWorth.player_id)
        .where(Player.is_ai.is_(False))
        .order_by(PlayerNetWorth.score_micro.desc())
    )
    net_worths = list(result.scalars().all())

    for rank, nw in enumerate(net_worths, 1):
        db.add(
            SeasonResult(
                season_id=season.id,
                player_id=nw.player_id,
                final_rank=rank,
                final_score_micro=nw.score_micro,
                final_net_worth_micro=nw.net_worth_micro,
            )
        )

    await db.commit()

    return SeasonActionResponse(
        season_id=season.id,
        season_number=season.season_number,
        action="end",
        message=f"Season {season.season_number} ended at tick {current_tick}",
    )