import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import AccountEntityType, EntryType, LedgerEntry
from app.models.player import Player
from app.models.treasury import SystemAccount


class InsufficientBalance(Exception):
    """Raised when source account lacks funds for the transfer."""

    def __init__(self, account_id: uuid.UUID, available: int, requested: int):
        self.account_id = account_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"Account {account_id}: has {available}, needs {requested}"
        )


async def _load_and_lock(
    session: AsyncSession,
    account_type: AccountEntityType,
    account_id: uuid.UUID,
):
    """SELECT FOR UPDATE the account row, return the ORM object."""
    if account_type == AccountEntityType.PLAYER:
        stmt = (
            select(Player)
            .where(Player.id == account_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise ValueError(f"Player {account_id} not found")
        return account

    if account_type == AccountEntityType.SYSTEM:
        stmt = (
            select(SystemAccount)
            .where(SystemAccount.id == account_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise ValueError(f"SystemAccount {account_id} not found")
        return account

    # GUILD will be added in Phase 6
    raise ValueError(f"Unsupported account type: {account_type}")


async def transfer(
    session: AsyncSession,
    from_type: AccountEntityType,
    from_id: uuid.UUID,
    to_type: AccountEntityType,
    to_id: uuid.UUID,
    amount: int,
    entry_type: EntryType,
    memo: str | None = None,
    tick_id: int | None = None,
) -> LedgerEntry:
    """
    Atomic double-entry transfer.

    Must be called inside an active transaction (session not yet committed).
    Caller is responsible for commit/rollback.
    """
    if amount <= 0:
        raise ValueError(f"Transfer amount must be positive, got {amount}")

    # Lock both accounts (consistent ordering: debit first, then credit)
    source = await _load_and_lock(session, from_type, from_id)
    dest = await _load_and_lock(session, to_type, to_id)

    # Check balance
    if source.balance_micro < amount:
        raise InsufficientBalance(from_id, source.balance_micro, amount)

    # Debit / Credit
    source.balance_micro -= amount
    dest.balance_micro += amount

    # Ledger entry
    entry = LedgerEntry(
        tick_id=tick_id,
        debit_type=from_type,
        debit_id=from_id,
        credit_type=to_type,
        credit_id=to_id,
        amount_micro=amount,
        entry_type=entry_type,
        memo=memo,
    )
    session.add(entry)

    return entry