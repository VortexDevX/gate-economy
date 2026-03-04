import hashlib

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gate import Gate, GateShare, GateStatus
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

    Returns 64-char hex digest.
    """
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

    # Build hash input
    parts = [f"treasury:{treasury_balance}"]
    for player_id, balance in player_rows:
        parts.append(f"player:{player_id}:{balance}")

    # Gate state — sorted by status name for determinism
    for status_name in sorted(status_counts.keys()):
        parts.append(f"gates:{status_name}:{status_counts[status_name]}")
    parts.append(f"stability_sum:{total_stability}")
    parts.append(f"shares_total:{total_shares}")

    hash_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()