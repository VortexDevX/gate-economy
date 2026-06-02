import hashlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gate import Gate, GateShare
from app.models.guild import Guild, GuildGateHolding, GuildShare
from app.models.leaderboard import Season, SeasonResult, SeasonStatus
from app.models.market import MarketPrice, Order, OrderSide, OrderStatus, Trade
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount


async def compute_state_hash(session: AsyncSession) -> str:
    """Compute a deterministic SHA-256 hash of the current economic state.

    Covers:
    - Treasury balance
    - Individual player balances ordered by ID
    - Gate counts per status
    - Sum of gate stabilities (truncated to int)
    - Total gate shares held
    - Open order count
    - Total escrow locked in open BUY orders
    - Total trade count

    Returns 64-char hex digest.
    """
    from sqlalchemy import text

    # Treasury balance
    result = await session.execute(
        select(SystemAccount.balance_micro).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury_balance = result.scalar_one()

    # Player balances ordered by ID for deterministic ordering
    result = await session.execute(
        select(Player.id, Player.balance_micro).order_by(text("id"))
    )
    player_rows = result.all()

    result = await session.execute(select(Gate).order_by(text("id")))
    gate_rows = result.scalars().all()

    result = await session.execute(
        select(GateShare).order_by(GateShare.gate_id, GateShare.player_id)
    )
    gate_share_rows = result.scalars().all()

    result = await session.execute(
        select(Order).order_by(Order.asset_type, Order.asset_id, Order.id)
    )
    order_rows = result.scalars().all()

    result = await session.execute(select(Trade).order_by(Trade.id))
    trade_rows = result.scalars().all()

    result = await session.execute(
        select(MarketPrice).order_by(MarketPrice.asset_type, MarketPrice.asset_id)
    )
    market_price_rows = result.scalars().all()

    result = await session.execute(select(Guild).order_by(text("id")))
    guild_rows = result.scalars().all()

    result = await session.execute(
        select(GuildShare).order_by(GuildShare.guild_id, GuildShare.player_id)
    )
    guild_share_rows = result.scalars().all()

    result = await session.execute(
        select(GuildGateHolding).order_by(
            GuildGateHolding.guild_id, GuildGateHolding.gate_id
        )
    )
    guild_holding_rows = result.scalars().all()

    result = await session.execute(select(Season).order_by(Season.id))
    season_rows = result.scalars().all()

    result = await session.execute(
        select(SeasonResult).order_by(
            SeasonResult.season_id, SeasonResult.final_rank, SeasonResult.player_id
        )
    )
    season_result_rows = result.scalars().all()

    # Gate counts per status
    result = await session.execute(
        select(
            Gate.status,
            func.count(Gate.id),
        ).group_by(Gate.status)
    )
    status_counts: dict[str, int] = {}
    for status, count in result.all():
        status_counts[status.value if hasattr(status, "value") else str(status)] = count

    # Sum of all gate stabilities (truncated to int for determinism)
    result = await session.execute(
        select(func.coalesce(func.sum(Gate.stability), 0.0))
    )
    total_stability = int(result.scalar_one())

    # Total shares held across all gates
    result = await session.execute(
        select(func.coalesce(func.sum(GateShare.quantity), 0))
    )
    total_shares = result.scalar_one()

    # Open order count
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
        )
    )
    open_orders = result.scalar_one()

    # Total escrow locked in open BUY orders
    result = await session.execute(
        select(func.coalesce(func.sum(Order.escrow_micro), 0)).where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            Order.side == OrderSide.BUY,
        )
    )
    total_escrow = result.scalar_one()

    # Total trade count
    result = await session.execute(
        select(func.count(Trade.id))
    )
    total_trades = result.scalar_one()

    # Guild treasury sum
    result = await session.execute(
        select(func.coalesce(func.sum(Guild.treasury_micro), 0))
    )
    guild_treasury_total = result.scalar_one()

    # Guild count per status
    result = await session.execute(
        select(Guild.status, func.count(Guild.id)).group_by(Guild.status)
    )
    guild_status_counts: dict[str, int] = {}
    for status, count in result.all():
        guild_status_counts[
            status.value if hasattr(status, "value") else str(status)
        ] = count

    # Season state
    result = await session.execute(
        select(func.count(Season.id)).where(
            Season.status == SeasonStatus.ACTIVE
        )
    )
    active_seasons = result.scalar_one()

    result = await session.execute(select(func.count(Season.id)))
    total_seasons = result.scalar_one()

    # Build hash input
    parts = [f"treasury:{treasury_balance}"]
    for player_id, balance in player_rows:
        parts.append(f"player:{player_id}:{balance}")

    for gate in gate_rows:
        parts.append(
            "gate:"
            f"{gate.id}:{gate.rank.value}:{gate.status.value}:"
            f"{round(gate.stability, 6)}:{round(gate.volatility, 6)}:"
            f"{gate.base_yield_micro}:{gate.total_shares}:"
            f"{gate.spawned_at_tick}:{gate.collapsed_at_tick}:"
            f"{gate.discovery_type.value}:{gate.discoverer_id}"
        )

    for share in gate_share_rows:
        parts.append(
            f"gate_share:{share.gate_id}:{share.player_id}:{share.quantity}"
        )

    for order in order_rows:
        parts.append(
            "order:"
            f"{order.id}:{order.player_id}:{order.asset_type.value}:"
            f"{order.asset_id}:{order.side.value}:{order.quantity}:"
            f"{order.price_limit_micro}:{order.filled_quantity}:"
            f"{order.escrow_micro}:{order.status.value}:"
            f"{order.created_at_tick}:{order.updated_at_tick}:"
            f"{order.is_system}:{order.guild_id}"
        )

    for trade in trade_rows:
        parts.append(
            "trade:"
            f"{trade.id}:{trade.buy_order_id}:{trade.sell_order_id}:"
            f"{trade.asset_type.value}:{trade.asset_id}:{trade.quantity}:"
            f"{trade.price_micro}:{trade.buyer_fee_micro}:"
            f"{trade.seller_fee_micro}:{trade.tick_id}"
        )

    for mp in market_price_rows:
        parts.append(
            "market_price:"
            f"{mp.asset_type.value}:{mp.asset_id}:{mp.last_price_micro}:"
            f"{mp.best_bid_micro}:{mp.best_ask_micro}:"
            f"{mp.volume_24h_micro}:{mp.updated_at_tick}"
        )

    # Gate state — sorted by status name for determinism
    for status_name in sorted(status_counts.keys()):
        parts.append(f"gates:{status_name}:{status_counts[status_name]}")
    parts.append(f"stability_sum:{total_stability}")
    parts.append(f"shares_total:{total_shares}")

    # Market state
    parts.append(f"open_orders:{open_orders}")
    parts.append(f"total_escrow:{total_escrow}")
    parts.append(f"total_trades:{total_trades}")

    # Guild state
    parts.append(f"guild_treasury:{guild_treasury_total}")
    for status_name in sorted(guild_status_counts.keys()):
        parts.append(f"guilds:{status_name}:{guild_status_counts[status_name]}")

    for guild in guild_rows:
        parts.append(
            "guild:"
            f"{guild.id}:{guild.name}:{guild.founder_id}:"
            f"{guild.treasury_micro}:{guild.total_shares}:"
            f"{guild.public_float_pct}:{guild.dividend_policy.value}:"
            f"{guild.auto_dividend_pct}:{guild.status.value}:"
            f"{guild.created_at_tick}:{guild.maintenance_cost_micro}:"
            f"{guild.missed_maintenance_ticks}:{guild.insolvent_ticks}"
        )

    for share in guild_share_rows:
        parts.append(
            f"guild_share:{share.guild_id}:{share.player_id}:{share.quantity}"
        )

    for holding in guild_holding_rows:
        parts.append(
            f"guild_holding:{holding.guild_id}:{holding.gate_id}:{holding.quantity}"
        )

    # Season state
    parts.append(f"seasons:{total_seasons}:{active_seasons}")

    for season in season_rows:
        parts.append(
            "season:"
            f"{season.id}:{season.season_number}:{season.start_tick}:"
            f"{season.end_tick}:{season.status.value}"
        )

    for result_row in season_result_rows:
        parts.append(
            "season_result:"
            f"{result_row.season_id}:{result_row.player_id}:"
            f"{result_row.final_rank}:{result_row.final_score_micro}:"
            f"{result_row.final_net_worth_micro}"
        )

    hash_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()
