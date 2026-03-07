import hashlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gate import Gate, GateShare
from app.models.market import Order, OrderStatus, OrderSide, Trade
from app.models.guild import Guild
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.models.leaderboard import Season, SeasonStatus


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
        
    # Season state
    parts.append(f"seasons:{total_seasons}:{active_seasons}")

    hash_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()