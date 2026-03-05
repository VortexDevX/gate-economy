"""Order matching engine.

Handles order placement, cancellation, price-time priority matching,
ISO management, and market price updates. All functions operate within
the tick's DB transaction — caller is responsible for commit.
"""

import uuid

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateRankProfile, GateShare, GateStatus
from app.models.guild import Guild, GuildGateHolding, GuildShare, GuildStatus
from app.models.intent import Intent, IntentStatus
from app.models.ledger import AccountEntityType, EntryType
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
)
from app.models.player import Player
from app.services.fee_calculator import calculate_escrow, calculate_fee
from app.services.transfer import transfer

logger = structlog.get_logger()


# ── Helpers ──


def calculate_iso_price(profile: GateRankProfile) -> int:
    avg_yield = (profile.yield_min_micro + profile.yield_max_micro) // 2
    return avg_yield * settings.iso_payback_ticks // profile.total_shares


async def _get_available_shares(
    session: AsyncSession, player_id: uuid.UUID,
    asset_type: AssetType, asset_id: uuid.UUID,
) -> int:
    """Owned shares minus shares committed to open sell orders."""
    if asset_type == AssetType.GATE_SHARE:
        result = await session.execute(
            select(GateShare.quantity).where(and_(
                GateShare.gate_id == asset_id, GateShare.player_id == player_id,
            ))
        )
        owned = result.scalar_one_or_none() or 0
    elif asset_type == AssetType.GUILD_SHARE:
        result = await session.execute(
            select(GuildShare.quantity).where(and_(
                GuildShare.guild_id == asset_id, GuildShare.player_id == player_id,
            ))
        )
        owned = result.scalar_one_or_none() or 0
    else:
        owned = 0

    result = await session.execute(
        select(func.coalesce(
            func.sum(Order.quantity - Order.filled_quantity), 0
        )).where(and_(
            Order.player_id == player_id,
            Order.asset_type == asset_type,
            Order.asset_id == asset_id,
            Order.side == OrderSide.SELL,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        ))
    )
    return owned - result.scalar_one()


async def _validate_asset(
    session: AsyncSession, asset_type: AssetType, asset_id: uuid.UUID,
) -> str | None:
    """Return error string if asset not tradeable, else None."""
    if asset_type == AssetType.GATE_SHARE:
        result = await session.execute(select(Gate).where(Gate.id == asset_id))
        gate = result.scalar_one_or_none()
        if gate is None:
            return "Gate not found"
        if gate.status == GateStatus.COLLAPSED:
            return "Gate has collapsed"
        return None
    if asset_type == AssetType.GUILD_SHARE:
        result = await session.execute(select(Guild).where(Guild.id == asset_id))
        guild = result.scalar_one_or_none()
        if guild is None:
            return "Guild not found"
        if guild.status == GuildStatus.DISSOLVED:
            return "Guild is dissolved"
        return None
    return "Asset type not supported"


# ── ISO Management ──


async def create_iso_orders(
    session: AsyncSession, tick_number: int, treasury_id: uuid.UUID,
) -> None:
    """Create system SELL orders for OFFERING gates and guild float shares."""
    # Gate ISOs
    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.OFFERING)
    )
    for gate in result.scalars().all():
        exists = await session.execute(
            select(Order.id).where(and_(
                Order.asset_id == gate.id, Order.is_system.is_(True),
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).limit(1)
        )
        if exists.scalar_one_or_none() is not None:
            continue
        result2 = await session.execute(
            select(GateShare.quantity).where(and_(
                GateShare.gate_id == gate.id, GateShare.player_id == treasury_id,
            ))
        )
        qty = result2.scalar_one_or_none()
        if not qty or qty <= 0:
            continue
        result2 = await session.execute(
            select(GateRankProfile).where(GateRankProfile.rank == gate.rank)
        )
        profile = result2.scalar_one()
        iso_price = calculate_iso_price(profile)
        session.add(Order(
            player_id=treasury_id, asset_type=AssetType.GATE_SHARE,
            asset_id=gate.id, side=OrderSide.SELL, quantity=qty,
            price_limit_micro=iso_price, created_at_tick=tick_number,
            is_system=True,
        ))
        logger.info("iso_order_created", gate_id=str(gate.id), price=iso_price, qty=qty)

    # Guild share ISOs
    result = await session.execute(
        select(Guild).where(Guild.status == GuildStatus.ACTIVE)
    )
    for guild in result.scalars().all():
        r2 = await session.execute(
            select(GuildShare.quantity).where(and_(
                GuildShare.guild_id == guild.id, GuildShare.player_id == guild.id,
            ))
        )
        self_held = r2.scalar_one_or_none() or 0
        if self_held <= 0:
            continue
        exists = await session.execute(
            select(Order.id).where(and_(
                Order.asset_type == AssetType.GUILD_SHARE,
                Order.asset_id == guild.id, Order.guild_id == guild.id,
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).limit(1)
        )
        if exists.scalar_one_or_none() is not None:
            continue
        iso_price = settings.guild_creation_cost_micro // guild.total_shares
        session.add(Order(
            player_id=guild.id, guild_id=guild.id,
            asset_type=AssetType.GUILD_SHARE, asset_id=guild.id,
            side=OrderSide.SELL, quantity=self_held,
            price_limit_micro=iso_price, created_at_tick=tick_number,
        ))
        logger.info("guild_iso_created", guild_id=str(guild.id), price=iso_price, qty=self_held)


async def finalize_iso_transitions(
    session: AsyncSession, tick_number: int, treasury_id: uuid.UUID,
) -> None:
    """Transition OFFERING → ACTIVE when treasury holds 0 shares."""
    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.OFFERING).with_for_update()
    )
    for gate in result.scalars().all():
        result2 = await session.execute(
            select(GateShare.quantity).where(and_(
                GateShare.gate_id == gate.id, GateShare.player_id == treasury_id,
            ))
        )
        treasury_qty = result2.scalar_one_or_none() or 0
        if treasury_qty == 0:
            gate.status = GateStatus.ACTIVE
            result2 = await session.execute(
                select(Order).where(and_(
                    Order.asset_id == gate.id, Order.is_system.is_(True),
                    Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
                ))
            )
            for order in result2.scalars().all():
                order.status = OrderStatus.FILLED
                order.updated_at_tick = tick_number
            logger.info("gate_iso_complete", gate_id=str(gate.id))


# ── Order Cancellation ──


async def cancel_collapsed_gate_orders(
    session: AsyncSession, tick_number: int, tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Cancel open orders for collapsed gates and dissolved guilds."""
    # Collapsed gates
    result = await session.execute(
        select(Gate.id).where(Gate.status == GateStatus.COLLAPSED)
    )
    collapsed_ids = [r[0] for r in result.all()]
    if collapsed_ids:
        result = await session.execute(
            select(Order).where(and_(
                Order.asset_type == AssetType.GATE_SHARE,
                Order.asset_id.in_(collapsed_ids),
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).with_for_update()
        )
        for order in result.scalars().all():
            if order.side == OrderSide.BUY and order.escrow_micro > 0:
                to_type = AccountEntityType.GUILD if order.guild_id else AccountEntityType.PLAYER
                to_id = order.guild_id if order.guild_id else order.player_id
                await transfer(
                    session=session,
                    from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
                    to_type=to_type, to_id=to_id,
                    amount=order.escrow_micro, entry_type=EntryType.ESCROW_RELEASE,
                    tick_id=tick_id, memo=f"Gate collapsed: {order.asset_id}",
                )
                order.escrow_micro = 0
            order.status = OrderStatus.CANCELLED
            order.updated_at_tick = tick_number

    # Dissolved guilds — cleanup any remaining GUILD_SHARE orders
    result = await session.execute(
        select(Guild.id).where(Guild.status == GuildStatus.DISSOLVED)
    )
    dissolved_ids = [r[0] for r in result.all()]
    if dissolved_ids:
        result = await session.execute(
            select(Order).where(and_(
                Order.asset_type == AssetType.GUILD_SHARE,
                Order.asset_id.in_(dissolved_ids),
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).with_for_update()
        )
        for order in result.scalars().all():
            if order.side == OrderSide.BUY and order.escrow_micro > 0:
                await transfer(
                    session=session,
                    from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
                    to_type=AccountEntityType.PLAYER, to_id=order.player_id,
                    amount=order.escrow_micro, entry_type=EntryType.ESCROW_RELEASE,
                    tick_id=tick_id, memo=f"Guild dissolved: {order.asset_id}",
                )
                order.escrow_micro = 0
            order.status = OrderStatus.CANCELLED
            order.updated_at_tick = tick_number


# ── Intent Processing ──


async def process_place_order(
    session: AsyncSession, intent: Intent, tick_number: int,
    tick_id: int, treasury_id: uuid.UUID,
) -> None:
    """Validate and create an order from a PLACE_ORDER intent."""
    p = intent.payload or {}
    try:
        asset_type = AssetType(p["asset_type"])
        asset_id = uuid.UUID(str(p["asset_id"]))
        side = OrderSide(p["side"])
        quantity = int(p["quantity"])
        price_limit = int(p["price_limit_micro"])
    except (KeyError, ValueError) as e:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Invalid payload: {e}"
        return

    if quantity <= 0 or price_limit <= 0:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Quantity and price must be positive"
        return

    error = await _validate_asset(session, asset_type, asset_id)
    if error:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = error
        return

    # Total shares check
    total = None
    if asset_type == AssetType.GATE_SHARE:
        r = await session.execute(select(Gate.total_shares).where(Gate.id == asset_id))
        total = r.scalar_one_or_none()
    elif asset_type == AssetType.GUILD_SHARE:
        r = await session.execute(select(Guild.total_shares).where(Guild.id == asset_id))
        total = r.scalar_one_or_none()
    if total and quantity > total:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Quantity {quantity} exceeds total shares {total}"
        return

    if side == OrderSide.BUY:
        escrow_total, _ = calculate_escrow(quantity, price_limit)
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == intent.player_id)
        )
        balance = result.scalar_one_or_none()
        if balance is None or balance < escrow_total:
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = f"Insufficient balance for escrow ({escrow_total})"
            return
        await transfer(
            session=session,
            from_type=AccountEntityType.PLAYER, from_id=intent.player_id,
            to_type=AccountEntityType.SYSTEM, to_id=treasury_id,
            amount=escrow_total, entry_type=EntryType.ESCROW_LOCK,
            tick_id=tick_id, memo=f"Buy escrow: {quantity}x {asset_id}",
        )
        session.add(Order(
            player_id=intent.player_id, asset_type=asset_type,
            asset_id=asset_id, side=OrderSide.BUY,
            quantity=quantity, price_limit_micro=price_limit,
            escrow_micro=escrow_total, created_at_tick=tick_number,
        ))
    else:  # SELL
        available = await _get_available_shares(
            session, intent.player_id, asset_type, asset_id,
        )
        if available < quantity:
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = f"Insufficient shares: have {available}, need {quantity}"
            return
        session.add(Order(
            player_id=intent.player_id, asset_type=asset_type,
            asset_id=asset_id, side=OrderSide.SELL,
            quantity=quantity, price_limit_micro=price_limit,
            created_at_tick=tick_number,
        ))


async def process_cancel_order(
    session: AsyncSession, intent: Intent, tick_number: int,
    tick_id: int, treasury_id: uuid.UUID,
) -> None:
    """Cancel an open order, release escrow if BUY."""
    p = intent.payload or {}
    try:
        order_id = uuid.UUID(str(p["order_id"]))
    except (KeyError, ValueError) as e:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Invalid payload: {e}"
        return
    result = await session.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Order not found"
        return
    if order.player_id != intent.player_id:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Not your order"
        return
    if order.status not in (OrderStatus.OPEN, OrderStatus.PARTIAL):
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Cannot cancel {order.status.value} order"
        return
    if order.side == OrderSide.BUY and order.escrow_micro > 0:
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
            to_type=AccountEntityType.PLAYER, to_id=order.player_id,
            amount=order.escrow_micro, entry_type=EntryType.ESCROW_RELEASE,
            tick_id=tick_id, memo=f"Cancel order: {order_id}",
        )
        order.escrow_micro = 0
    order.status = OrderStatus.CANCELLED
    order.updated_at_tick = tick_number


# ── Trade Execution ──


async def _execute_trade(
    session: AsyncSession, buy_order: Order, sell_order: Order,
    trade_qty: int, trade_price: int,
    tick_number: int, tick_id: int, treasury_id: uuid.UUID,
) -> Trade:
    """Execute a single matched trade. Handles gate/guild shares and guild orders."""
    trade_value = trade_qty * trade_price
    buyer_fee = calculate_fee(trade_value)
    is_gate_iso = sell_order.is_system
    sell_is_guild = sell_order.guild_id is not None and not is_gate_iso
    buy_is_guild = buy_order.guild_id is not None
    seller_fee = 0 if (is_gate_iso or sell_is_guild) else calculate_fee(trade_value)

    # ── Currency settlement ──
    if is_gate_iso:
        pass  # escrow IS the payment
    elif sell_is_guild:
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
            to_type=AccountEntityType.GUILD, to_id=sell_order.guild_id,
            amount=trade_value, entry_type=EntryType.TRADE_SETTLEMENT,
            tick_id=tick_id,
            memo=f"Guild trade: {trade_qty} shares @ {trade_price}",
        )
    else:
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
            to_type=AccountEntityType.PLAYER, to_id=sell_order.player_id,
            amount=trade_value, entry_type=EntryType.TRADE_SETTLEMENT,
            tick_id=tick_id,
            memo=f"Trade: {trade_qty} shares @ {trade_price}",
        )
        if seller_fee > 0:
            await transfer(
                session=session,
                from_type=AccountEntityType.PLAYER,
                from_id=sell_order.player_id,
                to_type=AccountEntityType.SYSTEM, to_id=treasury_id,
                amount=seller_fee, entry_type=EntryType.TRADE_FEE,
                tick_id=tick_id, memo="Seller fee",
            )

    # ── Share transfer ──
    asset_type = buy_order.asset_type
    if asset_type == AssetType.GATE_SHARE:
        # Seller side (always GateShare)
        seller_pid = treasury_id if is_gate_iso else sell_order.player_id
        result = await session.execute(
            select(GateShare).where(and_(
                GateShare.gate_id == sell_order.asset_id,
                GateShare.player_id == seller_pid,
            )).with_for_update()
        )
        result.scalar_one().quantity -= trade_qty

        # Buyer side
        if buy_is_guild:
            result = await session.execute(
                select(GuildGateHolding).where(and_(
                    GuildGateHolding.guild_id == buy_order.guild_id,
                    GuildGateHolding.gate_id == buy_order.asset_id,
                )).with_for_update()
            )
            holding = result.scalar_one_or_none()
            if holding is None:
                session.add(GuildGateHolding(
                    guild_id=buy_order.guild_id,
                    gate_id=buy_order.asset_id, quantity=trade_qty,
                ))
            else:
                holding.quantity += trade_qty
        else:
            result = await session.execute(
                select(GateShare).where(and_(
                    GateShare.gate_id == buy_order.asset_id,
                    GateShare.player_id == buy_order.player_id,
                )).with_for_update()
            )
            buyer_shares = result.scalar_one_or_none()
            if buyer_shares is None:
                session.add(GateShare(
                    gate_id=buy_order.asset_id,
                    player_id=buy_order.player_id, quantity=trade_qty,
                ))
            else:
                buyer_shares.quantity += trade_qty

    elif asset_type == AssetType.GUILD_SHARE:
        gid = buy_order.asset_id
        # Seller
        result = await session.execute(
            select(GuildShare).where(and_(
                GuildShare.guild_id == gid,
                GuildShare.player_id == sell_order.player_id,
            )).with_for_update()
        )
        result.scalar_one().quantity -= trade_qty
        # Buyer
        result = await session.execute(
            select(GuildShare).where(and_(
                GuildShare.guild_id == gid,
                GuildShare.player_id == buy_order.player_id,
            )).with_for_update()
        )
        buyer_shares = result.scalar_one_or_none()
        if buyer_shares is None:
            session.add(GuildShare(
                guild_id=gid, player_id=buy_order.player_id,
                quantity=trade_qty,
            ))
        else:
            buyer_shares.quantity += trade_qty

    # ── Update orders ──
    consumed = trade_value + buyer_fee
    buy_order.escrow_micro -= consumed
    buy_order.filled_quantity += trade_qty
    buy_order.updated_at_tick = tick_number
    buy_order.status = (
        OrderStatus.FILLED if buy_order.remaining == 0 else OrderStatus.PARTIAL
    )
    if buy_order.status == OrderStatus.FILLED and buy_order.escrow_micro > 0:
        esc_type = AccountEntityType.GUILD if buy_is_guild else AccountEntityType.PLAYER
        esc_id = buy_order.guild_id if buy_is_guild else buy_order.player_id
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM, from_id=treasury_id,
            to_type=esc_type, to_id=esc_id,
            amount=buy_order.escrow_micro,
            entry_type=EntryType.ESCROW_RELEASE,
            tick_id=tick_id, memo="Excess escrow on fill",
        )
        buy_order.escrow_micro = 0

    sell_order.filled_quantity += trade_qty
    sell_order.updated_at_tick = tick_number
    sell_order.status = (
        OrderStatus.FILLED if sell_order.remaining == 0 else OrderStatus.PARTIAL
    )

    trade = Trade(
        buy_order_id=buy_order.id, sell_order_id=sell_order.id,
        asset_type=buy_order.asset_type, asset_id=buy_order.asset_id,
        quantity=trade_qty, price_micro=trade_price,
        buyer_fee_micro=buyer_fee, seller_fee_micro=seller_fee,
        tick_id=tick_id,
    )
    session.add(trade)
    logger.info("trade_executed", qty=trade_qty, price=trade_price, iso=is_gate_iso)
    return trade


# ── Order Matching ──


async def match_orders(
    session: AsyncSession, tick_number: int, tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Match buy/sell orders by price-time priority for all assets."""
    result = await session.execute(
        select(Order.asset_type, Order.asset_id).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
        ).distinct()
    )
    assets = result.all()

    for asset_type, asset_id in assets:
        result = await session.execute(
            select(Order).where(and_(
                Order.asset_type == asset_type,
                Order.asset_id == asset_id,
                Order.side == OrderSide.BUY,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).order_by(
                Order.price_limit_micro.desc(),
                Order.created_at_tick.asc(),
            ).with_for_update()
        )
        buys = list(result.scalars().all())

        result = await session.execute(
            select(Order).where(and_(
                Order.asset_type == asset_type,
                Order.asset_id == asset_id,
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )).order_by(
                Order.price_limit_micro.asc(),
                Order.created_at_tick.asc(),
            ).with_for_update()
        )
        sells = list(result.scalars().all())

        bi, si = 0, 0
        while bi < len(buys) and si < len(sells):
            bb, bs = buys[bi], sells[si]
            if bb.price_limit_micro < bs.price_limit_micro:
                break
            trade_qty = min(bb.remaining, bs.remaining)
            await _execute_trade(
                session, bb, bs, trade_qty, bs.price_limit_micro,
                tick_number, tick_id, treasury_id,
            )
            if bb.remaining == 0:
                bi += 1
            if bs.remaining == 0:
                si += 1


# ── Market Prices ──


async def update_market_prices(
    session: AsyncSession, tick_number: int, tick_id: int,
) -> None:
    """Refresh market_prices for assets with trades or open orders."""
    result = await session.execute(
        select(Trade.asset_type, Trade.asset_id)
        .where(Trade.tick_id == tick_id).distinct()
    )
    traded = set(result.all())

    result = await session.execute(
        select(Order.asset_type, Order.asset_id).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
        ).distinct()
    )
    with_orders = set(result.all())

    for asset_type, asset_id in traded | with_orders:
        r = await session.execute(
            select(Trade.price_micro).where(and_(
                Trade.asset_type == asset_type, Trade.asset_id == asset_id,
            )).order_by(Trade.created_at.desc()).limit(1)
        )
        last_price = r.scalar_one_or_none()

        r = await session.execute(
            select(func.max(Order.price_limit_micro)).where(and_(
                Order.asset_type == asset_type, Order.asset_id == asset_id,
                Order.side == OrderSide.BUY,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            ))
        )
        best_bid = r.scalar_one_or_none()

        r = await session.execute(
            select(func.min(Order.price_limit_micro)).where(and_(
                Order.asset_type == asset_type, Order.asset_id == asset_id,
                Order.side == OrderSide.SELL,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            ))
        )
        best_ask = r.scalar_one_or_none()

        r = await session.execute(
            select(func.coalesce(
                func.sum(Trade.quantity * Trade.price_micro), 0
            )).where(and_(
                Trade.asset_type == asset_type, Trade.asset_id == asset_id,
                Trade.tick_id == tick_id,
            ))
        )
        tick_vol = r.scalar_one()

        r = await session.execute(
            select(MarketPrice).where(and_(
                MarketPrice.asset_type == asset_type,
                MarketPrice.asset_id == asset_id,
            ))
        )
        mp = r.scalar_one_or_none()
        if mp is None:
            session.add(MarketPrice(
                asset_type=asset_type, asset_id=asset_id,
                last_price_micro=last_price,
                best_bid_micro=best_bid, best_ask_micro=best_ask,
                volume_24h_micro=tick_vol, updated_at_tick=tick_number,
            ))
        else:
            if last_price is not None:
                mp.last_price_micro = last_price
            mp.best_bid_micro = best_bid
            mp.best_ask_micro = best_ask
            mp.volume_24h_micro += tick_vol
            mp.updated_at_tick = tick_number