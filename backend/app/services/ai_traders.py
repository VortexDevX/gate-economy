"""AI trader strategies.

All functions run within the tick transaction. AI bots create orders
directly (not via intents) and use the same escrow/transfer system
as human players.  Deterministic via tick RNG.
"""

import uuid

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateRankProfile, GateShare, GateStatus
from app.models.ledger import AccountEntityType, EntryType
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
)
from app.models.player import Player
from app.services.fee_calculator import calculate_escrow
from app.services.transfer import InsufficientBalance, transfer
from app.simulation.rng import TickRNG

logger = structlog.get_logger()


# ─── Helpers ───────────────────────────────────────────────


async def _cancel_ai_orders(
    session: AsyncSession,
    player_id: uuid.UUID,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Cancel all OPEN/PARTIAL orders for an AI player, releasing escrow."""
    result = await session.execute(
        select(Order)
        .where(
            Order.player_id == player_id,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        )
        .with_for_update()
    )
    orders = list(result.scalars().all())

    for order in orders:
        if order.side == OrderSide.BUY and order.escrow_micro > 0:
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=AccountEntityType.PLAYER,
                to_id=player_id,
                amount=order.escrow_micro,
                entry_type=EntryType.ESCROW_RELEASE,
                memo=f"AI order cancel: {order.id}",
                tick_id=tick_id,
            )
            order.escrow_micro = 0
        order.status = OrderStatus.CANCELLED
        order.updated_at_tick = tick_number


async def _get_available_shares(
    session: AsyncSession,
    player_id: uuid.UUID,
    asset_type: AssetType,
    asset_id: uuid.UUID,
) -> int:
    """Shares available to sell (held minus committed to open sells)."""
    if asset_type != AssetType.GATE_SHARE:
        return 0  # AI only trades GATE_SHARE for now

    result = await session.execute(
        select(GateShare.quantity).where(
            GateShare.gate_id == asset_id,
            GateShare.player_id == player_id,
        )
    )
    held = result.scalar_one_or_none() or 0

    # Subtract shares already committed to open/partial sell orders
    result = await session.execute(
        select(
            func.coalesce(
                func.sum(Order.quantity - Order.filled_quantity), 0
            )
        ).where(
            Order.player_id == player_id,
            Order.asset_type == asset_type,
            Order.asset_id == asset_id,
            Order.side == OrderSide.SELL,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        )
    )
    committed = result.scalar_one()
    return max(0, held - committed)


async def _place_ai_buy(
    session: AsyncSession,
    player_id: uuid.UUID,
    asset_type: AssetType,
    asset_id: uuid.UUID,
    qty: int,
    price: int,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> bool:
    """Place a BUY order with escrow.  Returns False if insufficient funds."""
    if qty <= 0 or price <= 0:
        return False

    total_escrow, _ = calculate_escrow(qty, price)

    try:
        await transfer(
            session=session,
            from_type=AccountEntityType.PLAYER,
            from_id=player_id,
            to_type=AccountEntityType.SYSTEM,
            to_id=treasury_id,
            amount=total_escrow,
            entry_type=EntryType.ESCROW_LOCK,
            memo=f"AI buy escrow: {asset_type.value} {asset_id}",
            tick_id=tick_id,
        )
    except InsufficientBalance:
        return False

    session.add(
        Order(
            player_id=player_id,
            asset_type=asset_type,
            asset_id=asset_id,
            side=OrderSide.BUY,
            quantity=qty,
            price_limit_micro=price,
            escrow_micro=total_escrow,
            created_at_tick=tick_number,
        )
    )
    return True


async def _place_ai_sell(
    session: AsyncSession,
    player_id: uuid.UUID,
    asset_type: AssetType,
    asset_id: uuid.UUID,
    qty: int,
    price: int,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> bool:
    """Place a SELL order.  Returns False if insufficient shares."""
    if qty <= 0 or price <= 0:
        return False

    available = await _get_available_shares(session, player_id, asset_type, asset_id)
    if available < qty:
        return False

    session.add(
        Order(
            player_id=player_id,
            asset_type=asset_type,
            asset_id=asset_id,
            side=OrderSide.SELL,
            quantity=qty,
            price_limit_micro=price,
            created_at_tick=tick_number,
        )
    )
    return True


async def _get_reference_price(
    session: AsyncSession,
    asset_type: AssetType,
    asset_id: uuid.UUID,
    gate: Gate | None = None,
) -> int | None:
    """Reference price: last_price → best_ask → ISO estimate → None."""
    result = await session.execute(
        select(MarketPrice).where(
            MarketPrice.asset_type == asset_type,
            MarketPrice.asset_id == asset_id,
        )
    )
    mp = result.scalar_one_or_none()

    if mp is not None:
        if mp.last_price_micro is not None and mp.last_price_micro > 0:
            return mp.last_price_micro
        if mp.best_ask_micro is not None and mp.best_ask_micro > 0:
            return mp.best_ask_micro

    # ISO estimate for OFFERING gates
    if gate is not None and gate.status == GateStatus.OFFERING:
        iso_price = int(
            gate.base_yield_micro
            * (gate.stability / 100.0)
            * settings.iso_payback_ticks
        ) // gate.total_shares
        if iso_price > 0:
            return iso_price

    return None


# ─── Strategies ────────────────────────────────────────────


async def run_market_maker(
    session: AsyncSession,
    player: Player,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
    rng: TickRNG,
) -> None:
    """Cancel-and-replace: place spread orders on every tradeable gate."""
    await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
    await session.refresh(player)

    result = await session.execute(
        select(Gate).where(
            Gate.status.in_([
                GateStatus.OFFERING,
                GateStatus.ACTIVE,
                GateStatus.UNSTABLE,
            ])
        )
    )
    gates = list(result.scalars().all())
    if not gates:
        return

    rng.shuffle(gates)

    for gate in gates:
        ref_price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        if ref_price is None:
            continue

        buy_price = int(ref_price * (1 - settings.ai_mm_spread))
        sell_price = int(ref_price * (1 + settings.ai_mm_spread))
        qty = settings.ai_mm_order_qty

        if buy_price > 0:
            await _place_ai_buy(
                session, player.id, AssetType.GATE_SHARE, gate.id,
                qty, buy_price, tick_number, tick_id, treasury_id,
            )

        # Sell only if holding shares
        result = await session.execute(
            select(GateShare).where(
                GateShare.gate_id == gate.id,
                GateShare.player_id == player.id,
            )
        )
        holding = result.scalar_one_or_none()
        if holding is not None and holding.quantity > 0:
            sell_qty = min(qty, holding.quantity)
            await _place_ai_sell(
                session, player.id, AssetType.GATE_SHARE, gate.id,
                sell_qty, sell_price, tick_number, tick_id, treasury_id,
            )


async def run_value_investor(
    session: AsyncSession,
    player: Player,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
    rng: TickRNG,
) -> None:
    """Buy undervalued gates, sell overvalued ones based on DCF estimate."""
    await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
    await session.refresh(player)

    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.ACTIVE)
    )
    gates = list(result.scalars().all())
    if not gates:
        return

    result = await session.execute(select(GateRankProfile))
    profiles = {p.rank: p for p in result.scalars().all()}

    for gate in gates:
        profile = profiles.get(gate.rank)
        if profile is None:
            continue

        remaining_stability = max(
            gate.stability - profile.collapse_threshold, 0
        )
        est_remaining_ticks = remaining_stability / settings.gate_base_decay_rate
        if est_remaining_ticks <= 0:
            continue

        total_remaining_yield = int(
            gate.base_yield_micro
            * (gate.stability / 100.0)
            * est_remaining_ticks
        )
        fair_value = total_remaining_yield // gate.total_shares
        if fair_value <= 0:
            continue

        ref_price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        if ref_price is None:
            continue

        # BUY undervalued
        buy_threshold = int(fair_value * (1 - settings.ai_vi_buy_discount))
        if ref_price <= buy_threshold:
            await session.refresh(player)
            max_spend = player.balance_micro // 10  # max 10% per gate
            if max_spend > 0 and ref_price > 0:
                qty = min(max_spend // ref_price, settings.ai_mm_order_qty)
                if qty > 0:
                    await _place_ai_buy(
                        session, player.id, AssetType.GATE_SHARE, gate.id,
                        qty, ref_price, tick_number, tick_id, treasury_id,
                    )

        # SELL overvalued
        sell_threshold = int(fair_value * (1 + settings.ai_vi_sell_premium))
        if ref_price >= sell_threshold:
            result = await session.execute(
                select(GateShare).where(
                    GateShare.gate_id == gate.id,
                    GateShare.player_id == player.id,
                )
            )
            holding = result.scalar_one_or_none()
            if holding is not None and holding.quantity > 0:
                await _place_ai_sell(
                    session, player.id, AssetType.GATE_SHARE, gate.id,
                    holding.quantity, ref_price,
                    tick_number, tick_id, treasury_id,
                )


async def run_noise_trader(
    session: AsyncSession,
    player: Player,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
    rng: TickRNG,
) -> None:
    """Random buy/sell with price jitter on a random active gate."""
    await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
    await session.refresh(player)

    if rng.random() >= settings.ai_noise_activity:
        return  # skip this tick

    result = await session.execute(
        select(Gate, MarketPrice)
        .join(
            MarketPrice,
            and_(
                MarketPrice.asset_type == AssetType.GATE_SHARE,
                MarketPrice.asset_id == Gate.id,
            ),
        )
        .where(
            Gate.status == GateStatus.ACTIVE,
            MarketPrice.last_price_micro.isnot(None),
        )
    )
    rows = list(result.all())
    if not rows:
        return

    gate, mp = rng.choice(rows)
    ref_price = mp.last_price_micro

    side = OrderSide.BUY if rng.random() < 0.5 else OrderSide.SELL
    qty = rng.randint(1, settings.ai_noise_max_qty)
    price_factor = rng.uniform(0.90, 1.10)
    price = max(1, int(ref_price * price_factor))

    if side == OrderSide.BUY:
        await _place_ai_buy(
            session, player.id, AssetType.GATE_SHARE, gate.id,
            qty, price, tick_number, tick_id, treasury_id,
        )
    else:
        result = await session.execute(
            select(GateShare).where(
                GateShare.gate_id == gate.id,
                GateShare.player_id == player.id,
            )
        )
        holding = result.scalar_one_or_none()
        if holding is not None and holding.quantity > 0:
            sell_qty = min(qty, holding.quantity)
            await _place_ai_sell(
                session, player.id, AssetType.GATE_SHARE, gate.id,
                sell_qty, price, tick_number, tick_id, treasury_id,
            )


# ─── Orchestrator ──────────────────────────────────────────


async def run_ai_traders(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
    rng: TickRNG,
) -> None:
    """Run all AI trading strategies for this tick."""
    result = await session.execute(
        select(Player).where(Player.is_ai == True).with_for_update()  # noqa: E712
    )
    ai_players = {p.username: p for p in result.scalars().all()}

    if not ai_players:
        return

    if "ai_market_maker" in ai_players:
        await run_market_maker(
            session, ai_players["ai_market_maker"],
            tick_number, tick_id, treasury_id, rng,
        )

    if "ai_value_investor" in ai_players:
        await run_value_investor(
            session, ai_players["ai_value_investor"],
            tick_number, tick_id, treasury_id, rng,
        )

    if "ai_noise_trader" in ai_players:
        await run_noise_trader(
            session, ai_players["ai_noise_trader"],
            tick_number, tick_id, treasury_id, rng,
        )