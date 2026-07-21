"""Player-facing market projections built from authoritative economy tables."""

import uuid
from collections import defaultdict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateRankProfile, GateShare, GateStatus
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
    MarketAssetResponse,
    MarketHistoryPoint,
    MarketHistoryResponse,
    MarketOverviewResponse,
)
from app.schemas.player import (
    GatePositionResponse,
    GuildPositionResponse,
    PortfolioResponse,
)
from app.services.instrument_identity import gate_display_name, gate_ticker


def _gate_mark_price(gate: Gate, market: MarketPrice | None) -> int:
    if gate.status == GateStatus.COLLAPSED:
        return 0
    if market is not None:
        if market.last_price_micro and market.last_price_micro > 0:
            return market.last_price_micro
        if market.best_bid_micro and market.best_ask_micro:
            return (market.best_bid_micro + market.best_ask_micro) // 2
        if market.best_bid_micro:
            return market.best_bid_micro
        if market.best_ask_micro:
            return market.best_ask_micro
    return (
        int(gate.base_yield_micro * (gate.stability / 100.0))
        * settings.iso_payback_ticks
        // max(1, gate.total_shares)
    )


def _guild_mark_price(guild: Guild, market: MarketPrice | None) -> int:
    if guild.status == GuildStatus.DISSOLVED:
        return 0
    if market is not None:
        if market.last_price_micro and market.last_price_micro > 0:
            return market.last_price_micro
        if market.best_bid_micro and market.best_ask_micro:
            return (market.best_bid_micro + market.best_ask_micro) // 2
        if market.best_bid_micro:
            return market.best_bid_micro
        if market.best_ask_micro:
            return market.best_ask_micro
    return settings.guild_creation_cost_micro // max(1, guild.total_shares)


def _risk_band(gate: Gate, collapse_threshold: float) -> str:
    if gate.status == GateStatus.COLLAPSED:
        return "COLLAPSED"
    if gate.status == GateStatus.OFFERING:
        return "OFFERING"
    if gate.status == GateStatus.UNSTABLE or gate.stability <= collapse_threshold:
        return "CRITICAL"
    if gate.stability - collapse_threshold <= 15:
        return "WATCH"
    return "STABLE"


def _concentration_multiplier(ownership_pct: float) -> float:
    if ownership_pct > 0.90:
        return 0.30
    if ownership_pct > 0.75:
        return 0.60
    if ownership_pct > 0.50:
        return 0.80
    return 1.0


async def build_portfolio(
    session: AsyncSession,
    player: Player,
) -> PortfolioResponse:
    """Build one account projection without client-side N+1 requests."""
    tick_result = await session.execute(select(func.max(Tick.tick_number)))
    as_of_tick = tick_result.scalar_one_or_none() or 0

    reserved_result = await session.execute(
        select(func.coalesce(func.sum(Order.escrow_micro), 0)).where(
            Order.player_id == player.id,
            Order.side == OrderSide.BUY,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        )
    )
    reserved_cash = int(reserved_result.scalar_one())

    gate_result = await session.execute(
        select(GateShare, Gate, GateRankProfile, MarketPrice)
        .join(Gate, GateShare.gate_id == Gate.id)
        .join(GateRankProfile, Gate.rank == GateRankProfile.rank)
        .outerjoin(
            MarketPrice,
            and_(
                MarketPrice.asset_type == AssetType.GATE_SHARE,
                MarketPrice.asset_id == Gate.id,
            ),
        )
        .where(GateShare.player_id == player.id, GateShare.quantity > 0)
        .order_by(Gate.status, Gate.rank, Gate.id)
    )

    gate_positions: list[GatePositionResponse] = []
    gate_value = 0
    projected_yield = 0
    unstable_exposure = 0
    for holding, gate, profile, market in gate_result.all():
        ownership = holding.quantity / max(1, gate.total_shares)
        effective_yield = (
            int(gate.base_yield_micro * (gate.stability / 100.0))
            if gate.status == GateStatus.ACTIVE
            else 0
        )
        position_yield = int(
            (effective_yield * holding.quantity // max(1, gate.total_shares))
            * _concentration_multiplier(ownership)
        )
        mark = _gate_mark_price(gate, market)
        value = mark * holding.quantity
        risk = _risk_band(gate, profile.collapse_threshold)
        gate_value += value
        projected_yield += position_yield
        if risk in {"WATCH", "CRITICAL"}:
            unstable_exposure += value
        gate_positions.append(
            GatePositionResponse(
                gate_id=gate.id,
                ticker=gate_ticker(gate.id, gate.rank.value),
                display_name=gate_display_name(gate.id),
                rank=gate.rank.value,
                status=gate.status.value,
                quantity=holding.quantity,
                total_shares=gate.total_shares,
                ownership_pct=round(ownership * 100, 2),
                stability=round(gate.stability, 2),
                collapse_threshold=profile.collapse_threshold,
                base_yield_micro=gate.base_yield_micro,
                effective_yield_micro=effective_yield,
                projected_yield_micro=position_yield,
                mark_price_micro=mark,
                market_value_micro=value,
                best_bid_micro=market.best_bid_micro if market else None,
                best_ask_micro=market.best_ask_micro if market else None,
                volume_24h_micro=market.volume_24h_micro if market else 0,
                risk_band=risk,
            )
        )

    guild_result = await session.execute(
        select(GuildShare, Guild, MarketPrice)
        .join(Guild, GuildShare.guild_id == Guild.id)
        .outerjoin(
            MarketPrice,
            and_(
                MarketPrice.asset_type == AssetType.GUILD_SHARE,
                MarketPrice.asset_id == Guild.id,
            ),
        )
        .where(GuildShare.player_id == player.id, GuildShare.quantity > 0)
        .order_by(Guild.status, Guild.name)
    )

    guild_positions: list[GuildPositionResponse] = []
    guild_value = 0
    for holding, guild, market in guild_result.all():
        mark = _guild_mark_price(guild, market)
        value = mark * holding.quantity
        guild_value += value
        guild_positions.append(
            GuildPositionResponse(
                guild_id=guild.id,
                name=guild.name,
                status=guild.status.value,
                quantity=holding.quantity,
                total_shares=guild.total_shares,
                ownership_pct=round(
                    holding.quantity / max(1, guild.total_shares) * 100,
                    2,
                ),
                treasury_micro=guild.treasury_micro,
                mark_price_micro=mark,
                market_value_micro=value,
                best_bid_micro=market.best_bid_micro if market else None,
                best_ask_micro=market.best_ask_micro if market else None,
                volume_24h_micro=market.volume_24h_micro if market else 0,
            )
        )

    portfolio_value = gate_value + guild_value
    return PortfolioResponse(
        as_of_tick=as_of_tick,
        cash_balance_micro=player.balance_micro,
        reserved_cash_micro=reserved_cash,
        gate_value_micro=gate_value,
        guild_value_micro=guild_value,
        portfolio_value_micro=portfolio_value,
        net_worth_micro=player.balance_micro + reserved_cash + portfolio_value,
        projected_yield_per_tick_micro=projected_yield,
        unstable_exposure_micro=unstable_exposure,
        gate_positions=gate_positions,
        guild_positions=guild_positions,
    )


async def build_market_overview(
    session: AsyncSession,
    *,
    status: GateStatus | None,
    rank: str | None,
    sort_by: str,
    offset: int,
    limit: int,
) -> MarketOverviewResponse:
    """Build gate scanner rows with comparable yield, risk, and liquidity."""
    count_result = await session.execute(
        select(Gate.status, func.count(Gate.id)).group_by(Gate.status)
    )
    status_counts: defaultdict[str, int] = defaultdict(int)
    for gate_status, count in count_result.all():
        status_counts[gate_status.value] = count

    query = (
        select(Gate, GateRankProfile, MarketPrice)
        .join(GateRankProfile, Gate.rank == GateRankProfile.rank)
        .outerjoin(
            MarketPrice,
            and_(
                MarketPrice.asset_type == AssetType.GATE_SHARE,
                MarketPrice.asset_id == Gate.id,
            ),
        )
    )
    if status is not None:
        query = query.where(Gate.status == status)
    if rank is not None:
        query = query.where(Gate.rank == rank)

    result = await session.execute(query)
    items: list[MarketAssetResponse] = []
    for gate, profile, market in result.all():
        effective_yield = (
            int(gate.base_yield_micro * (gate.stability / 100.0))
            if gate.status == GateStatus.ACTIVE
            else 0
        )
        yield_per_share = effective_yield // max(1, gate.total_shares)
        mark = _gate_mark_price(gate, market)
        spread_bps = None
        if market and market.best_bid_micro and market.best_ask_micro and mark > 0:
            spread_bps = int(
                (market.best_ask_micro - market.best_bid_micro) * 10_000 / mark
            )
        yield_rate = (
            int(yield_per_share * 10_000 / mark)
            if yield_per_share > 0 and mark > 0
            else None
        )
        items.append(
            MarketAssetResponse(
                asset_id=gate.id,
                ticker=gate_ticker(gate.id, gate.rank.value),
                display_name=gate_display_name(gate.id),
                rank=gate.rank.value,
                status=gate.status.value,
                stability=round(gate.stability, 2),
                collapse_threshold=profile.collapse_threshold,
                distance_to_instability=round(
                    max(0.0, gate.stability - profile.collapse_threshold),
                    2,
                ),
                risk_band=_risk_band(gate, profile.collapse_threshold),
                total_shares=gate.total_shares,
                base_yield_micro=gate.base_yield_micro,
                effective_yield_micro=effective_yield,
                yield_per_share_micro=yield_per_share,
                mark_price_micro=mark,
                yield_rate_bps_per_tick=yield_rate,
                last_price_micro=market.last_price_micro if market else None,
                best_bid_micro=market.best_bid_micro if market else None,
                best_ask_micro=market.best_ask_micro if market else None,
                spread_bps=spread_bps,
                volume_24h_micro=market.volume_24h_micro if market else 0,
                updated_at_tick=market.updated_at_tick if market else 0,
                spawned_at_tick=gate.spawned_at_tick,
                discovery_type=gate.discovery_type.value,
            )
        )

    if sort_by == "YIELD":
        items.sort(
            key=lambda item: (
                item.yield_rate_bps_per_tick or -1,
                item.volume_24h_micro,
            ),
            reverse=True,
        )
    elif sort_by == "RISK":
        risk_order = {"CRITICAL": 0, "WATCH": 1, "OFFERING": 2, "STABLE": 3, "COLLAPSED": 4}
        items.sort(key=lambda item: (risk_order[item.risk_band], -item.volume_24h_micro))
    elif sort_by == "NEWEST":
        items.sort(key=lambda item: item.spawned_at_tick, reverse=True)
    else:
        items.sort(
            key=lambda item: (item.volume_24h_micro, item.spawned_at_tick),
            reverse=True,
        )

    total = len(items)
    return MarketOverviewResponse(
        items=items[offset : offset + limit],
        total=total,
        active_count=status_counts[GateStatus.ACTIVE.value],
        offering_count=status_counts[GateStatus.OFFERING.value],
        unstable_count=status_counts[GateStatus.UNSTABLE.value],
        collapsed_count=status_counts[GateStatus.COLLAPSED.value],
    )


async def build_market_history(
    session: AsyncSession,
    asset_type: AssetType,
    asset_id: uuid.UUID,
    limit: int,
) -> MarketHistoryResponse:
    """Aggregate recent executed trades into one OHLC point per logical tick."""
    tick_result = await session.execute(
        select(Tick.tick_number)
        .join(Trade, Trade.tick_id == Tick.id)
        .where(Trade.asset_type == asset_type, Trade.asset_id == asset_id)
        .distinct()
        .order_by(Tick.tick_number.desc())
        .limit(limit)
    )
    tick_numbers = [row[0] for row in tick_result.all()]
    if not tick_numbers:
        return MarketHistoryResponse(
            asset_type=asset_type.value,
            asset_id=asset_id,
            points=[],
        )

    trade_result = await session.execute(
        select(Tick.tick_number, Trade)
        .join(Trade, Trade.tick_id == Tick.id)
        .where(
            Trade.asset_type == asset_type,
            Trade.asset_id == asset_id,
            Tick.tick_number.in_(tick_numbers),
        )
        .order_by(Tick.tick_number, Trade.created_at, Trade.id)
    )
    grouped: defaultdict[int, list[Trade]] = defaultdict(list)
    for tick_number, trade in trade_result.all():
        grouped[tick_number].append(trade)

    points: list[MarketHistoryPoint] = []
    for tick_number in sorted(grouped):
        trades = grouped[tick_number]
        prices = [trade.price_micro for trade in trades]
        volume_quantity = sum(trade.quantity for trade in trades)
        volume_micro = sum(trade.quantity * trade.price_micro for trade in trades)
        points.append(
            MarketHistoryPoint(
                tick_number=tick_number,
                open_micro=prices[0],
                high_micro=max(prices),
                low_micro=min(prices),
                close_micro=prices[-1],
                average_price_micro=volume_micro // max(1, volume_quantity),
                volume_quantity=volume_quantity,
                volume_micro=volume_micro,
                trade_count=len(trades),
            )
        )

    return MarketHistoryResponse(
        asset_type=asset_type.value,
        asset_id=asset_id,
        points=points,
    )
