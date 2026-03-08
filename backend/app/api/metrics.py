from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    generate_latest,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.event import Event
from app.models.gate import Gate, GateStatus
from app.models.intent import Intent, IntentStatus
from app.models.market import Order, OrderStatus, Trade
from app.models.player import Player
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount

router = APIRouter(tags=["metrics"])

REGISTRY = CollectorRegistry()

dge_tick_number = Gauge("dge_tick_number", "Current tick number", registry=REGISTRY)
dge_tick_duration_seconds = Gauge(
    "dge_tick_duration_seconds", "Last tick duration in seconds", registry=REGISTRY
)
dge_intent_queue_depth = Gauge(
    "dge_intent_queue_depth", "Queued intents", registry=REGISTRY
)
dge_active_players_total = Gauge(
    "dge_active_players_total", "Registered human players", registry=REGISTRY
)
dge_treasury_balance_micro = Gauge(
    "dge_treasury_balance_micro", "Treasury balance in micro-units", registry=REGISTRY
)
dge_trade_volume_micro = Gauge(
    "dge_trade_volume_micro", "Total trade volume in micro-units", registry=REGISTRY
)
dge_active_gates_total = Gauge(
    "dge_active_gates_total", "Non-collapsed gates", registry=REGISTRY
)
dge_ws_connections = Gauge(
    "dge_ws_connections", "Current WebSocket connections", registry=REGISTRY
)
dge_order_book_depth = Gauge(
    "dge_order_book_depth", "Open/partial orders", registry=REGISTRY
)
dge_events_fired_total = Gauge(
    "dge_events_fired_total", "Total events fired", registry=REGISTRY
)


async def _refresh(db: AsyncSession) -> None:
    """Query DB and set all gauge values."""
    # Latest tick
    result = await db.execute(
        select(Tick).order_by(Tick.tick_number.desc()).limit(1)
    )
    tick = result.scalar_one_or_none()
    if tick:
        dge_tick_number.set(tick.tick_number)
        if tick.started_at and tick.completed_at:
            duration = (tick.completed_at - tick.started_at).total_seconds()
            dge_tick_duration_seconds.set(duration)
        else:
            dge_tick_duration_seconds.set(0)
    else:
        dge_tick_number.set(0)
        dge_tick_duration_seconds.set(0)

    # Intent queue
    result = await db.execute(
        select(func.count()).select_from(Intent).where(
            Intent.status == IntentStatus.QUEUED
        )
    )
    dge_intent_queue_depth.set(result.scalar_one())

    # Human players
    result = await db.execute(
        select(func.count()).select_from(Player).where(Player.is_ai.is_(False))
    )
    dge_active_players_total.set(result.scalar_one())

    # Treasury
    result = await db.execute(
        select(SystemAccount.balance_micro).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    dge_treasury_balance_micro.set(result.scalar_one_or_none() or 0)

    # Trade volume
    result = await db.execute(
        select(func.coalesce(func.sum(Trade.price_micro * Trade.quantity), 0))
    )
    dge_trade_volume_micro.set(result.scalar_one())

    # Active gates
    result = await db.execute(
        select(func.count()).select_from(Gate).where(
            Gate.status.in_([GateStatus.ACTIVE, GateStatus.OFFERING, GateStatus.UNSTABLE])
        )
    )
    dge_active_gates_total.set(result.scalar_one())

    # Order book
    result = await db.execute(
        select(func.count()).select_from(Order).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
        )
    )
    dge_order_book_depth.set(result.scalar_one())

    # Events
    result = await db.execute(select(func.count()).select_from(Event))
    dge_events_fired_total.set(result.scalar_one())


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    await _refresh(db)
    return Response(
        content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
    )