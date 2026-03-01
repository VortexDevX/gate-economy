from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_player, get_db
from app.models.ledger import AccountEntityType, LedgerEntry
from app.models.player import Player
from app.schemas.player import LedgerEntryResponse, PaginatedLedger, PlayerResponse

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/me", response_model=PlayerResponse)
async def get_me(
    player: Player = Depends(get_current_player),
):
    return player


@router.get("/me/ledger", response_model=PaginatedLedger)
async def get_my_ledger(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated ledger entries where the player is debited or credited."""
    base_filter = (
        (
            (LedgerEntry.debit_type == AccountEntityType.PLAYER)
            & (LedgerEntry.debit_id == player.id)
        )
        | (
            (LedgerEntry.credit_type == AccountEntityType.PLAYER)
            & (LedgerEntry.credit_id == player.id)
        )
    )

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(LedgerEntry).where(base_filter)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * size
    rows_result = await db.execute(
        select(LedgerEntry)
        .where(base_filter)
        .order_by(LedgerEntry.id.desc())
        .offset(offset)
        .limit(size)
    )
    items = list(rows_result.scalars().all())

    return PaginatedLedger(
        items=[LedgerEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        size=size,
    )