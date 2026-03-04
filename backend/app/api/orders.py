from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_player, get_db
from app.models.market import Order
from app.models.player import Player
from app.schemas.market import OrderListResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/me", response_model=OrderListResponse)
async def my_orders(
    player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List current player's orders (all statuses), most recent first."""
    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.player_id == player.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Order)
        .where(Order.player_id == player.id)
        .order_by(Order.created_at_tick.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()

    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
    )