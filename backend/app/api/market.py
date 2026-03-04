import uuid as _uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
)
from app.schemas.market import (
    MarketPriceResponse,
    OrderBookEntry,
    OrderBookResponse,
    TradeListResponse,
    TradeResponse,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/{asset_type}/{asset_id}", response_model=MarketPriceResponse)
async def get_market_price(
    asset_type: AssetType,
    asset_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Current price, best bid/ask, and volume for an asset."""
    result = await db.execute(
        select(MarketPrice).where(
            and_(
                MarketPrice.asset_type == asset_type,
                MarketPrice.asset_id == asset_id,
            )
        )
    )
    mp = result.scalar_one_or_none()
    if mp is None:
        return MarketPriceResponse(
            asset_type=asset_type.value,
            asset_id=asset_id,
        )
    return MarketPriceResponse.model_validate(mp)


@router.get("/{asset_type}/{asset_id}/book", response_model=OrderBookResponse)
async def get_order_book(
    asset_type: AssetType,
    asset_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Aggregated order book — bids descending, asks ascending."""
    # Bids: grouped by price, highest first
    result = await db.execute(
        select(
            Order.price_limit_micro,
            func.sum(Order.quantity - Order.filled_quantity).label("total_qty"),
            func.count(Order.id).label("cnt"),
        )
        .where(
            and_(
                Order.asset_type == asset_type,
                Order.asset_id == asset_id,
                Order.side == OrderSide.BUY,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )
        )
        .group_by(Order.price_limit_micro)
        .order_by(Order.price_limit_micro.desc())
    )
    bids = [
        OrderBookEntry(
            price_micro=row[0], total_quantity=row[1], order_count=row[2],
        )
        for row in result.all()
    ]

    # Asks: grouped by price, lowest first
    result = await db.execute(
        select(
            Order.price_limit_micro,
            func.sum(Order.quantity - Order.filled_quantity).label("total_qty"),
            func.count(Order.id).label("cnt"),
        )
        .where(
            and_(
                Order.asset_type == asset_type,
                Order.asset_id == asset_id,
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )
        )
        .group_by(Order.price_limit_micro)
        .order_by(Order.price_limit_micro.asc())
    )
    asks = [
        OrderBookEntry(
            price_micro=row[0], total_quantity=row[1], order_count=row[2],
        )
        for row in result.all()
    ]

    return OrderBookResponse(bids=bids, asks=asks)


@router.get(
    "/{asset_type}/{asset_id}/trades", response_model=TradeListResponse,
)
async def get_trades(
    asset_type: AssetType,
    asset_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Recent trades for an asset, most recent first."""
    count_result = await db.execute(
        select(func.count(Trade.id)).where(
            and_(
                Trade.asset_type == asset_type,
                Trade.asset_id == asset_id,
            )
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Trade)
        .where(
            and_(
                Trade.asset_type == asset_type,
                Trade.asset_id == asset_id,
            )
        )
        .order_by(Trade.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    trades = result.scalars().all()

    return TradeListResponse(
        trades=[TradeResponse.model_validate(t) for t in trades],
        total=total,
    )