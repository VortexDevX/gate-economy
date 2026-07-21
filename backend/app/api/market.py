import uuid as _uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_player, get_db
from app.models.gate import Gate, GateRank, GateShare, GateStatus
from app.models.guild import Guild, GuildShare, GuildStatus
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
)
from app.models.player import Player
from app.models.tick import Tick
from app.schemas.market import (
    MarketHistoryResponse,
    MarketOverviewResponse,
    MarketPriceResponse,
    OrderBookEntry,
    OrderBookResponse,
    OrderPreviewRequest,
    OrderPreviewResponse,
    TradeListResponse,
    TradeResponse,
)
from app.services.fee_calculator import calculate_escrow, calculate_fee
from app.services.market_read_models import (
    build_market_history,
    build_market_overview,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/order-preview", response_model=OrderPreviewResponse)
async def preview_order(
    preview: OrderPreviewRequest,
    db: AsyncSession = Depends(get_db),
    player: Player = Depends(get_current_player),
) -> OrderPreviewResponse:
    """Return exact current fee/escrow and position availability without mutation."""
    gross = preview.quantity * preview.price_limit_micro
    fee = calculate_fee(gross)
    escrow, _ = calculate_escrow(preview.quantity, preview.price_limit_micro)
    available_shares = 0
    total_shares: int | None = None
    asset_error: str | None = None

    if preview.asset_type == AssetType.GATE_SHARE:
        asset_result = await db.execute(
            select(Gate.total_shares, Gate.status).where(Gate.id == preview.asset_id)
        )
        asset = asset_result.one_or_none()
        if asset is None:
            asset_error = "Gate not found"
        elif asset.status == GateStatus.COLLAPSED:
            asset_error = "Gate has collapsed"
        else:
            total_shares = asset.total_shares
        holding_result = await db.execute(
            select(GateShare.quantity).where(
                GateShare.gate_id == preview.asset_id,
                GateShare.player_id == player.id,
            )
        )
        available_shares = holding_result.scalar_one_or_none() or 0
    else:
        asset_result = await db.execute(
            select(Guild.total_shares, Guild.status).where(
                Guild.id == preview.asset_id
            )
        )
        asset = asset_result.one_or_none()
        if asset is None:
            asset_error = "Guild not found"
        elif asset.status == GuildStatus.DISSOLVED:
            asset_error = "Guild is dissolved"
        else:
            total_shares = asset.total_shares
        holding_result = await db.execute(
            select(GuildShare.quantity).where(
                GuildShare.guild_id == preview.asset_id,
                GuildShare.player_id == player.id,
            )
        )
        available_shares = holding_result.scalar_one_or_none() or 0

    if preview.side == OrderSide.SELL and available_shares > 0:
        committed_result = await db.execute(
            select(
                func.coalesce(func.sum(Order.quantity - Order.filled_quantity), 0)
            ).where(
                Order.player_id == player.id,
                Order.asset_type == preview.asset_type,
                Order.asset_id == preview.asset_id,
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )
        )
        available_shares = max(
            0,
            available_shares - int(committed_result.scalar_one()),
        )

    reason = asset_error
    if reason is None and total_shares and preview.quantity > total_shares:
        reason = f"Quantity exceeds total issue ({total_shares})"
    if reason is None and preview.side == OrderSide.BUY and player.balance_micro < escrow:
        reason = "Insufficient available cash for required escrow"
    if reason is None and preview.side == OrderSide.SELL and available_shares < preview.quantity:
        reason = f"Only {available_shares} shares available to sell"

    return OrderPreviewResponse(
        gross_value_micro=gross,
        estimated_fee_micro=fee,
        fee_rate_bps=int(fee * 10_000 / gross) if gross > 0 else 0,
        required_escrow_micro=(escrow if preview.side == OrderSide.BUY else 0),
        available_cash_micro=player.balance_micro,
        available_shares=available_shares,
        can_submit=reason is None,
        reason=reason,
    )


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    db: AsyncSession = Depends(get_db),
    status: GateStatus | None = Query(None),
    rank: GateRank | None = Query(None),
    sort_by: Literal["VOLUME", "YIELD", "RISK", "NEWEST"] = Query("VOLUME"),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
) -> MarketOverviewResponse:
    """Gate scanner with comparable yield, collapse risk, spread, and volume."""
    return await build_market_overview(
        db,
        status=status,
        rank=rank.value if rank else None,
        sort_by=sort_by,
        offset=offset,
        limit=limit,
    )


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
        select(Trade, Tick.tick_number)
        .outerjoin(Tick, Trade.tick_id == Tick.id)
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
    trades = result.all()

    return TradeListResponse(
        trades=[
            TradeResponse.model_validate(trade).model_copy(
                update={"tick_number": tick_number}
            )
            for trade, tick_number in trades
        ],
        total=total,
    )


@router.get(
    "/{asset_type}/{asset_id}/history",
    response_model=MarketHistoryResponse,
)
async def get_market_history(
    asset_type: AssetType,
    asset_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=60, ge=1, le=200),
) -> MarketHistoryResponse:
    """Recent per-tick OHLC trade history for one asset."""
    return await build_market_history(db, asset_type, asset_id, limit)
