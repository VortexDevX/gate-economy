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
    """treasury + SUM(player_balances) must equal INITIAL_SEED at all times."""
    num_players = 5
    for _ in range(num_players):
        tag = uuid.uuid4().hex[:8]
        resp = await client.post("/auth/register", json={
            "username": f"cons_{tag}",
            "email": f"cons_{tag}@test.com",
            "password": "securepass123",
        })
        assert resp.status_code == 201

    # Separate engine to read committed state
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        result = await session.execute(
            select(SystemAccount.balance_micro).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_balance = result.scalar_one()

        result = await session.execute(
            select(func.coalesce(func.sum(Player.balance_micro), 0))
        )
        player_total = result.scalar_one()

    await engine.dispose()

    total = treasury_balance + player_total
    assert total == settings.initial_seed_micro, (
        f"Conservation violated: treasury={treasury_balance} "
        f"+ players={player_total} = {total} "
        f"!= {settings.initial_seed_micro}"
    )