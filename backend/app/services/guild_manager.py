"""Guild management — creation, dividends, investment, maintenance, dissolution."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateStatus
from app.models.guild import (
    DividendPolicy,
    Guild,
    GuildGateHolding,
    GuildMember,
    GuildRole,
    GuildShare,
    GuildStatus,
)
from app.models.intent import Intent, IntentStatus
from app.models.ledger import AccountEntityType, EntryType
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
)
from app.services.fee_calculator import calculate_fee
from app.services.transfer import InsufficientBalance, transfer

logger = structlog.get_logger()


# ── Intent processors ──


async def process_create_guild(
    session: AsyncSession,
    intent: Intent,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Process a CREATE_GUILD intent."""
    payload = intent.payload or {}
    name = payload.get("name")
    public_float_pct = payload.get("public_float_pct", 0.0)
    dividend_policy_str = payload.get("dividend_policy", "MANUAL")
    auto_dividend_pct = payload.get("auto_dividend_pct")

    # Validate name
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Guild name is required"
        return
    name = name.strip()

    result = await session.execute(
        select(Guild.id).where(Guild.name == name).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Guild name '{name}' is already taken"
        return

    # Validate float pct
    if not isinstance(public_float_pct, (int, float)):
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "public_float_pct must be a number"
        return
    public_float_pct = float(public_float_pct)
    if public_float_pct < 0 or public_float_pct > settings.guild_max_float_pct:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = (
            f"public_float_pct must be between 0 and {settings.guild_max_float_pct}"
        )
        return

    # Validate dividend policy
    try:
        dividend_policy = DividendPolicy(dividend_policy_str)
    except ValueError:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Invalid dividend policy: {dividend_policy_str}"
        return

    if dividend_policy == DividendPolicy.AUTO_FIXED_PCT:
        if auto_dividend_pct is None or not isinstance(
            auto_dividend_pct, (int, float)
        ):
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = (
                "auto_dividend_pct required for AUTO_FIXED_PCT policy"
            )
            return
        auto_dividend_pct = float(auto_dividend_pct)
        if auto_dividend_pct <= 0 or auto_dividend_pct > 1.0:
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = (
                "auto_dividend_pct must be > 0 and <= 1.0"
            )
            return

    # Charge creation fee
    try:
        await transfer(
            session=session,
            from_type=AccountEntityType.PLAYER,
            from_id=intent.player_id,
            to_type=AccountEntityType.SYSTEM,
            to_id=treasury_id,
            amount=settings.guild_creation_cost_micro,
            entry_type=EntryType.GUILD_CREATION,
            memo=f"Guild creation: {name}",
            tick_id=tick_id,
        )
    except InsufficientBalance:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = (
            f"Insufficient balance for guild creation "
            f"(cost: {settings.guild_creation_cost_micro})"
        )
        return

    # Create guild record
    total_shares = settings.guild_total_shares
    guild = Guild(
        name=name,
        founder_id=intent.player_id,
        treasury_micro=0,
        total_shares=total_shares,
        public_float_pct=public_float_pct,
        dividend_policy=dividend_policy,
        auto_dividend_pct=(
            auto_dividend_pct
            if dividend_policy == DividendPolicy.AUTO_FIXED_PCT
            else None
        ),
        status=GuildStatus.ACTIVE,
        created_at_tick=tick_number,
        maintenance_cost_micro=settings.guild_base_maintenance_micro,
    )
    session.add(guild)
    await session.flush()

    # Membership
    session.add(GuildMember(
        guild_id=guild.id,
        player_id=intent.player_id,
        role=GuildRole.LEADER,
        joined_at_tick=tick_number,
    ))

    # Share allocation
    founder_shares = total_shares - int(total_shares * public_float_pct)
    float_shares = total_shares - founder_shares

    session.add(GuildShare(
        guild_id=guild.id,
        player_id=intent.player_id,
        quantity=founder_shares,
    ))
    if float_shares > 0:
        session.add(GuildShare(
            guild_id=guild.id,
            player_id=guild.id,  # guild holds own ISO float
            quantity=float_shares,
        ))

    logger.info(
        "guild_created",
        guild_id=str(guild.id),
        name=name,
        founder_shares=founder_shares,
        float_shares=float_shares,
    )


async def process_guild_dividend(
    session: AsyncSession,
    intent: Intent,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Process GUILD_DIVIDEND intent — manual dividend distribution."""
    payload = intent.payload or {}
    guild_id_str = payload.get("guild_id")
    amount_micro = payload.get("amount_micro")

    if not guild_id_str:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "guild_id is required"
        return
    try:
        guild_id = uuid.UUID(guild_id_str)
    except (ValueError, TypeError):
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Invalid guild_id"
        return

    result = await session.execute(
        select(Guild).where(Guild.id == guild_id).with_for_update()
    )
    guild = result.scalar_one_or_none()
    if guild is None:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Guild not found"
        return
    if guild.status != GuildStatus.ACTIVE:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Guild is {guild.status.value}, must be ACTIVE"
        return

    # Leader check
    result = await session.execute(
        select(GuildMember.role).where(
            GuildMember.guild_id == guild_id,
            GuildMember.player_id == intent.player_id,
        )
    )
    role = result.scalar_one_or_none()
    if role != GuildRole.LEADER:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Only the guild leader can issue dividends"
        return

    # Determine amount
    if amount_micro is not None:
        if not isinstance(amount_micro, int) or amount_micro <= 0:
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = "amount_micro must be a positive integer"
            return
        if amount_micro > guild.treasury_micro:
            intent.status = IntentStatus.REJECTED
            intent.reject_reason = "Guild treasury has insufficient funds"
            return
    else:
        amount_micro = guild.treasury_micro

    if amount_micro <= 0:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Guild treasury is empty"
        return

    await _distribute_dividend(session, guild, amount_micro, tick_id)


async def process_guild_invest(
    session: AsyncSession,
    intent: Intent,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Process GUILD_INVEST intent — guild places BUY order for gate shares."""
    payload = intent.payload or {}
    guild_id_str = payload.get("guild_id")
    gate_id_str = payload.get("gate_id")
    quantity = payload.get("quantity")
    price_limit_micro = payload.get("price_limit_micro")

    if not guild_id_str or not gate_id_str:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "guild_id and gate_id are required"
        return
    try:
        guild_id = uuid.UUID(guild_id_str)
        gate_id = uuid.UUID(gate_id_str)
    except (ValueError, TypeError):
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Invalid guild_id or gate_id"
        return

    if not isinstance(quantity, int) or quantity <= 0:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "quantity must be a positive integer"
        return
    if not isinstance(price_limit_micro, int) or price_limit_micro <= 0:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "price_limit_micro must be a positive integer"
        return

    # Load guild
    result = await session.execute(
        select(Guild).where(Guild.id == guild_id).with_for_update()
    )
    guild = result.scalar_one_or_none()
    if guild is None:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Guild not found"
        return
    if guild.status != GuildStatus.ACTIVE:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Guild is {guild.status.value}, must be ACTIVE"
        return

    # Leader check
    result = await session.execute(
        select(GuildMember.role).where(
            GuildMember.guild_id == guild_id,
            GuildMember.player_id == intent.player_id,
        )
    )
    role = result.scalar_one_or_none()
    if role != GuildRole.LEADER:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Only the guild leader can invest"
        return

    # Validate gate
    result = await session.execute(select(Gate).where(Gate.id == gate_id))
    gate = result.scalar_one_or_none()
    if gate is None:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Gate not found"
        return
    if gate.status == GateStatus.COLLAPSED:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = "Gate has collapsed"
        return

    # Escrow calculation
    trade_value = quantity * price_limit_micro
    max_fee = calculate_fee(trade_value)
    escrow = trade_value + max_fee

    if guild.treasury_micro < escrow:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = (
            f"Guild treasury insufficient for escrow "
            f"(need {escrow}, have {guild.treasury_micro})"
        )
        return

    # Lock escrow from guild treasury
    await transfer(
        session=session,
        from_type=AccountEntityType.GUILD,
        from_id=guild_id,
        to_type=AccountEntityType.SYSTEM,
        to_id=treasury_id,
        amount=escrow,
        entry_type=EntryType.ESCROW_LOCK,
        memo=f"Guild invest escrow: gate {gate_id}",
        tick_id=tick_id,
    )

    session.add(Order(
        player_id=guild.id,
        guild_id=guild.id,
        asset_type=AssetType.GATE_SHARE,
        asset_id=gate_id,
        side=OrderSide.BUY,
        quantity=quantity,
        price_limit_micro=price_limit_micro,
        escrow_micro=escrow,
        created_at_tick=tick_number,
    ))

    logger.info(
        "guild_invest_order",
        guild_id=str(guild_id),
        gate_id=str(gate_id),
        quantity=quantity,
        escrow=escrow,
    )


# ── Per-tick lifecycle ──


async def guild_maintenance(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Charge maintenance for all ACTIVE/INSOLVENT guilds each tick."""
    result = await session.execute(
        select(Guild)
        .where(Guild.status.in_([GuildStatus.ACTIVE, GuildStatus.INSOLVENT]))
        .with_for_update()
    )
    guilds = list(result.scalars().all())

    for guild in guilds:
        # Calculate cost = base + scaled on gate holding value
        h_result = await session.execute(
            select(GuildGateHolding).where(
                GuildGateHolding.guild_id == guild.id,
                GuildGateHolding.quantity > 0,
            )
        )
        holdings = list(h_result.scalars().all())

        gate_value = 0
        for h in holdings:
            p_result = await session.execute(
                select(MarketPrice.last_price_micro).where(
                    MarketPrice.asset_type == AssetType.GATE_SHARE,
                    MarketPrice.asset_id == h.gate_id,
                )
            )
            price = p_result.scalar_one_or_none() or 0
            gate_value += h.quantity * price

        cost = settings.guild_base_maintenance_micro + int(
            gate_value * settings.guild_maintenance_scale
        )
        guild.maintenance_cost_micro = cost

        if guild.treasury_micro >= cost:
            await transfer(
                session=session,
                from_type=AccountEntityType.GUILD,
                from_id=guild.id,
                to_type=AccountEntityType.SYSTEM,
                to_id=treasury_id,
                amount=cost,
                entry_type=EntryType.GUILD_MAINTENANCE,
                memo=f"Maintenance tick {tick_number}",
                tick_id=tick_id,
            )
            guild.missed_maintenance_ticks = 0
            if guild.status == GuildStatus.INSOLVENT:
                guild.insolvent_ticks = 0
                guild.status = GuildStatus.ACTIVE
                logger.info("guild_recovered", guild_id=str(guild.id))
        else:
            if guild.treasury_micro > 0:
                await transfer(
                    session=session,
                    from_type=AccountEntityType.GUILD,
                    from_id=guild.id,
                    to_type=AccountEntityType.SYSTEM,
                    to_id=treasury_id,
                    amount=guild.treasury_micro,
                    entry_type=EntryType.GUILD_MAINTENANCE,
                    memo=f"Partial maintenance tick {tick_number}",
                    tick_id=tick_id,
                )
            guild.missed_maintenance_ticks += 1

        # Insolvency transition
        if (
            guild.missed_maintenance_ticks >= settings.guild_insolvency_threshold
            and guild.status == GuildStatus.ACTIVE
        ):
            guild.status = GuildStatus.INSOLVENT
            guild.insolvent_ticks = 0
            logger.info(
                "guild_insolvent",
                guild_id=str(guild.id),
                missed=guild.missed_maintenance_ticks,
            )

        # Dissolution check
        if guild.status == GuildStatus.INSOLVENT:
            guild.insolvent_ticks += 1
            if guild.insolvent_ticks >= settings.guild_dissolution_threshold:
                await _dissolve_guild(
                    session, guild, tick_number, tick_id, treasury_id
                )


async def auto_dividends(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
) -> None:
    """Distribute automatic dividends for AUTO_FIXED_PCT guilds."""
    result = await session.execute(
        select(Guild)
        .where(
            Guild.status == GuildStatus.ACTIVE,
            Guild.dividend_policy == DividendPolicy.AUTO_FIXED_PCT,
        )
        .with_for_update()
    )
    guilds = list(result.scalars().all())

    for guild in guilds:
        if guild.treasury_micro <= 0 or guild.auto_dividend_pct is None:
            continue
        amount = int(guild.treasury_micro * float(guild.auto_dividend_pct))
        if amount <= 0:
            continue
        await _distribute_dividend(session, guild, amount, tick_id)


# ── Internal helpers ──


async def _distribute_dividend(
    session: AsyncSession,
    guild: Guild,
    amount: int,
    tick_id: int,
) -> None:
    """Distribute amount from guild treasury to shareholders pro-rata.

    Skips guild-held shares (no self-payment).
    Integer division remainder stays in guild treasury.
    """
    result = await session.execute(
        select(GuildShare).where(
            GuildShare.guild_id == guild.id,
            GuildShare.player_id != guild.id,
            GuildShare.quantity > 0,
        )
    )
    shareholders = list(result.scalars().all())
    if not shareholders:
        return

    total_shares = sum(s.quantity for s in shareholders)
    if total_shares <= 0:
        return

    shareholders.sort(key=lambda s: str(s.player_id))

    for sh in shareholders:
        payout = amount * sh.quantity // total_shares
        if payout <= 0:
            continue
        await transfer(
            session=session,
            from_type=AccountEntityType.GUILD,
            from_id=guild.id,
            to_type=AccountEntityType.PLAYER,
            to_id=sh.player_id,
            amount=payout,
            entry_type=EntryType.DIVIDEND,
            memo=f"Dividend from guild {guild.id}",
            tick_id=tick_id,
        )


async def _dissolve_guild(
    session: AsyncSession,
    guild: Guild,
    tick_number: int,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Dissolve guild: liquidate holdings, distribute, cancel orders, sweep."""
    guild.status = GuildStatus.DISSOLVED
    logger.info("guild_dissolved", guild_id=str(guild.id))

    # 1. Liquidate gate holdings at discount
    result = await session.execute(
        select(GuildGateHolding).where(
            GuildGateHolding.guild_id == guild.id,
            GuildGateHolding.quantity > 0,
        )
    )
    for holding in result.scalars().all():
        p_result = await session.execute(
            select(MarketPrice.last_price_micro).where(
                MarketPrice.asset_type == AssetType.GATE_SHARE,
                MarketPrice.asset_id == holding.gate_id,
            )
        )
        price = p_result.scalar_one_or_none() or 0
        liq_value = int(
            holding.quantity * price * settings.guild_liquidation_discount
        )
        if liq_value > 0:
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=AccountEntityType.GUILD,
                to_id=guild.id,
                amount=liq_value,
                entry_type=EntryType.TRADE_SETTLEMENT,
                memo=f"Dissolution liquidate gate {holding.gate_id}",
                tick_id=tick_id,
            )
        holding.quantity = 0

    # 2. Cancel guild's own open orders, release escrow back to guild
    result = await session.execute(
        select(Order)
        .where(
            Order.guild_id == guild.id,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        )
        .with_for_update()
    )
    for order in result.scalars().all():
        order.status = OrderStatus.CANCELLED
        order.updated_at_tick = tick_number
        if order.escrow_micro > 0:
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=AccountEntityType.GUILD,
                to_id=guild.id,
                amount=order.escrow_micro,
                entry_type=EntryType.ESCROW_RELEASE,
                memo=f"Dissolution cancel order {order.id}",
                tick_id=tick_id,
            )
            order.escrow_micro = 0

    # 3. Distribute remaining treasury to shareholders
    if guild.treasury_micro > 0:
        await _distribute_dividend(session, guild, guild.treasury_micro, tick_id)

    # 4. Cancel open GUILD_SHARE orders for this guild's shares
    result = await session.execute(
        select(Order)
        .where(
            Order.asset_type == AssetType.GUILD_SHARE,
            Order.asset_id == guild.id,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        )
        .with_for_update()
    )
    for order in result.scalars().all():
        order.status = OrderStatus.CANCELLED
        order.updated_at_tick = tick_number
        if order.escrow_micro > 0 and order.side == OrderSide.BUY:
            if order.guild_id is not None:
                to_type = AccountEntityType.GUILD
                to_id = order.guild_id
            else:
                to_type = AccountEntityType.PLAYER
                to_id = order.player_id
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=to_type,
                to_id=to_id,
                amount=order.escrow_micro,
                entry_type=EntryType.ESCROW_RELEASE,
                memo=f"Dissolution cancel share order {order.id}",
                tick_id=tick_id,
            )
            order.escrow_micro = 0

    # 5. Sweep any remaining guild treasury to system treasury
    if guild.treasury_micro > 0:
        await transfer(
            session=session,
            from_type=AccountEntityType.GUILD,
            from_id=guild.id,
            to_type=AccountEntityType.SYSTEM,
            to_id=treasury_id,
            amount=guild.treasury_micro,
            entry_type=EntryType.GUILD_MAINTENANCE,
            memo="Dissolution final sweep",
            tick_id=tick_id,
        )