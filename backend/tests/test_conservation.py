import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount


@pytest.mark.asyncio
async def test_conservation_after_registrations(client: AsyncClient):
    """treasury + SUM(player_balances) must equal INITIAL_SEED at all times.

    Uses a snapshot approach: measure state before and after registrations.
    This makes the test immune to players created by other tests.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # ── Snapshot BEFORE ──
    async with factory() as session:
        result = await session.execute(
            select(SystemAccount.balance_micro).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_before = result.scalar_one()

        result = await session.execute(
            select(func.coalesce(func.sum(Player.balance_micro), 0))
        )
        players_before = int(result.scalar_one())

    total_before = treasury_before + players_before

    # ── Register 5 new players ──
    num_players = 5
    for _ in range(num_players):
        tag = uuid.uuid4().hex[:8]
        resp = await client.post("/auth/register", json={
            "username": f"cons_{tag}",
            "email": f"cons_{tag}@test.com",
            "password": "securepass123",
        })
        assert resp.status_code == 201

    # ── Snapshot AFTER ──
    async with factory() as session:
        result = await session.execute(
            select(SystemAccount.balance_micro).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_after = result.scalar_one()

        result = await session.execute(
            select(func.coalesce(func.sum(Player.balance_micro), 0))
        )
        players_after = int(result.scalar_one())

    await engine.dispose()

    total_after = treasury_after + players_after

    # ── Conservation: total must not change ──
    assert total_before == total_after, (
        f"Conservation violated: "
        f"before={total_before} (treasury={treasury_before} + players={players_before}), "
        f"after={total_after} (treasury={treasury_after} + players={players_after})"
    )

    # ── Verify the treasury decreased by exactly the grants issued ──
    expected_grant_total = num_players * settings.starting_balance_micro
    actual_treasury_decrease = treasury_before - treasury_after
    assert actual_treasury_decrease == expected_grant_total, (
        f"Treasury decrease {actual_treasury_decrease} != "
        f"expected {expected_grant_total} ({num_players} × {settings.starting_balance_micro})"
    )