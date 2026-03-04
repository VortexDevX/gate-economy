"""Gate API routes — read-only views of gate state."""

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.deps import DBSession # type: ignore
from app.models.gate import Gate, GateRankProfile, GateShare, GateStatus
from app.schemas.gate import (
    GateDetailResponse,
    GateListResponse,
    GateRankProfileResponse,
    GateResponse,
    ShareholderInfo,
)

router = APIRouter(prefix="/gates", tags=["gates"])


@router.get("/rank-profiles", response_model=list[GateRankProfileResponse])
async def list_rank_profiles(session: DBSession):
    """Return all gate rank profiles (reference data)."""
    result = await session.execute(
        select(GateRankProfile).order_by(GateRankProfile.spawn_weight.desc())
    )
    profiles = result.scalars().all()
    return [GateRankProfileResponse.model_validate(p) for p in profiles]


@router.get("", response_model=GateListResponse)
async def list_gates(
    session: DBSession,
    status: str | None = Query(None, description="Filter by status"),
    rank: str | None = Query(None, description="Filter by rank"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List gates with optional filters and pagination."""
    query = select(Gate)
    count_query = select(func.count(Gate.id))

    # Apply filters
    if status is not None:
        try:
            status_enum = GateStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status: {status}. Valid: {[s.value for s in GateStatus]}",
            )
        query = query.where(Gate.status == status_enum)
        count_query = count_query.where(Gate.status == status_enum)

    if rank is not None:
        query = query.where(Gate.rank == rank)
        count_query = count_query.where(Gate.rank == rank)

    # Total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Fetch page
    query = query.order_by(Gate.spawned_at_tick.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    gates = result.scalars().all()

    return GateListResponse(
        gates=[GateResponse.model_validate(g) for g in gates],
        total=total,
    )


@router.get("/{gate_id}", response_model=GateDetailResponse)
async def get_gate(session: DBSession, gate_id: uuid.UUID):
    """Get gate detail including shareholder breakdown."""
    result = await session.execute(select(Gate).where(Gate.id == gate_id))
    gate = result.scalar_one_or_none()
    if gate is None:
        raise HTTPException(status_code=404, detail="Gate not found")

    # Load shareholders
    share_result = await session.execute(
        select(GateShare)
        .where(GateShare.gate_id == gate_id, GateShare.quantity > 0)
        .order_by(GateShare.quantity.desc())
    )
    shares = list(share_result.scalars().all())

    total_held = sum(s.quantity for s in shares)
    shareholders = [
        ShareholderInfo(
            player_id=s.player_id,
            quantity=s.quantity,
            percentage=round(
                (s.quantity / total_held * 100) if total_held > 0 else 0, 2
            ),
        )
        for s in shares
    ]

    gate_data = GateResponse.model_validate(gate).model_dump()
    return GateDetailResponse(**gate_data, shareholders=shareholders)