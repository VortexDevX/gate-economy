import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import AccountEntityType, EntryType
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.transfer import InsufficientBalance, transfer


async def _get_treasury(db: AsyncSession) -> SystemAccount:
    result = await db.execute(
        select(SystemAccount).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    return result.scalar_one()


async def _make_player(db: AsyncSession, balance: int = 0) -> Player:
    player = Player(
        id=uuid.uuid4(),
        username=f"test_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="nothashed",
        balance_micro=balance,
    )
    db.add(player)
    await db.flush()
    return player


@pytest.mark.asyncio
async def test_transfer_success(db: AsyncSession):
    treasury = await _get_treasury(db)
    original_balance = treasury.balance_micro
    player = await _make_player(db, balance=0)

    amount = 5_000_000
    entry = await transfer(
        session=db,
        from_type=AccountEntityType.SYSTEM,
        from_id=treasury.id,
        to_type=AccountEntityType.PLAYER,
        to_id=player.id,
        amount=amount,
        entry_type=EntryType.STARTING_GRANT,
        memo="test grant",
    )

    assert player.balance_micro == amount
    assert treasury.balance_micro == original_balance - amount
    assert entry.amount_micro == amount
    assert entry.entry_type == EntryType.STARTING_GRANT
    assert entry.debit_id == treasury.id
    assert entry.credit_id == player.id


@pytest.mark.asyncio
async def test_transfer_insufficient_balance(db: AsyncSession):
    p1 = await _make_player(db, balance=100)
    p2 = await _make_player(db, balance=0)

    with pytest.raises(InsufficientBalance):
        await transfer(
            session=db,
            from_type=AccountEntityType.PLAYER,
            from_id=p1.id,
            to_type=AccountEntityType.PLAYER,
            to_id=p2.id,
            amount=200,
            entry_type=EntryType.TRADE_SETTLEMENT,
        )

    # Balances must be unchanged — no partial mutation
    assert p1.balance_micro == 100
    assert p2.balance_micro == 0


@pytest.mark.asyncio
async def test_transfer_zero_amount(db: AsyncSession):
    with pytest.raises(ValueError, match="positive"):
        await transfer(
            session=db,
            from_type=AccountEntityType.PLAYER,
            from_id=uuid.uuid4(),
            to_type=AccountEntityType.PLAYER,
            to_id=uuid.uuid4(),
            amount=0,
            entry_type=EntryType.TRADE_SETTLEMENT,
        )


@pytest.mark.asyncio
async def test_transfer_negative_amount(db: AsyncSession):
    with pytest.raises(ValueError, match="positive"):
        await transfer(
            session=db,
            from_type=AccountEntityType.PLAYER,
            from_id=uuid.uuid4(),
            to_type=AccountEntityType.PLAYER,
            to_id=uuid.uuid4(),
            amount=-500,
            entry_type=EntryType.TRADE_SETTLEMENT,
        )