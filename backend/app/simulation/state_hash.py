import hashlib

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount


async def compute_state_hash(session: AsyncSession) -> str:
    """Compute a deterministic SHA-256 hash of the current economic state.

    Covers:
    - Treasury balance
    - Sum of all player balances
    - Individual player balances ordered by ID (for determinism)

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
        select(Player.id, Player.balance_micro)
        .order_by(text("id"))
    )
    player_rows = result.all()

    # Build hash input
    parts = [f"treasury:{treasury_balance}"]
    for player_id, balance in player_rows:
        parts.append(f"player:{player_id}:{balance}")

    hash_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()