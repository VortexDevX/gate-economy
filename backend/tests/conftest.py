import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis as RedisClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.deps import get_db
from app.main import app
from app.models.gate import Gate, GateShare
from app.models.intent import Intent
from app.models.ledger import LedgerEntry
from app.models.player import Player
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.models.market import MarketPrice, Order, Trade
from app.models.guild import Guild, GuildGateHolding, GuildMember, GuildShare
from app.models.event import Event
from app.models.news import News


def _make_engine():
    return create_async_engine(settings.database_url, poolclass=NullPool)


def _make_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _reset_database(factory) -> None:
    """Wipe all test data and reset treasury to INITIAL_SEED."""
    async with factory() as session:
        # Delete in FK-safe order
        await session.execute(delete(Event))
        await session.execute(delete(News))
        await session.execute(delete(Intent))
        await session.execute(delete(GuildGateHolding))
        await session.execute(delete(GuildShare))
        await session.execute(delete(GuildMember))
        await session.execute(delete(Guild))
        await session.execute(delete(Trade))
        await session.execute(delete(Order))
        await session.execute(delete(MarketPrice))
        await session.execute(delete(GateShare))
        await session.execute(delete(Gate))
        await session.execute(delete(LedgerEntry))
        await session.execute(delete(Player))
        await session.execute(delete(Tick))

        # Reset or create treasury
        result = await session.execute(
            select(SystemAccount).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury = result.scalar_one_or_none()
        if treasury is None:
            session.add(
                SystemAccount(
                    account_type=AccountType.TREASURY,
                    balance_micro=settings.initial_seed_micro,
                )
            )
        else:
            treasury.balance_micro = settings.initial_seed_micro
        await session.commit()


# ── Autouse: clean slate before every test ──


@pytest_asyncio.fixture(autouse=True)
async def _clean_state():
    """Reset DB to pristine state before each test.

    Ensures no test can poison another via committed state.
    Treasury restored to INITIAL_SEED, all players/gates/ticks wiped.
    """
    engine = _make_engine()
    factory = _make_factory(engine)
    await _reset_database(factory)
    await engine.dispose()
    yield


# ── Core fixtures ──


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Self-contained DB session for service-level tests."""
    engine = _make_engine()
    factory = _make_factory(engine)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Self-contained HTTPX client with its own engine."""
    engine = _make_engine()
    factory = _make_factory(engine)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory():
    """Session factory for direct simulation/service testing."""
    engine = _make_engine()
    factory = _make_factory(engine)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client():
    """Redis client for lock/cache tests."""
    client = RedisClient.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def pause_simulation(redis_client):
    """Hold the simulation lock to prevent the worker from running ticks."""
    from app.simulation.lock import LOCK_KEY

    for _ in range(20):
        result = await redis_client.set(
            LOCK_KEY, "test-runner", nx=True, ex=300
        )
        if result:
            break
        await asyncio.sleep(0.5)
    else:
        await redis_client.set(LOCK_KEY, "test-runner", ex=300)
    yield
    await redis_client.delete(LOCK_KEY)


@pytest_asyncio.fixture
async def test_player_id(session_factory) -> uuid.UUID:
    """Create a disposable test player with zero balance.

    Balance is 0 because this player is not created through
    the registration flow — no treasury debit occurs.
    Giving it a nonzero balance would violate conservation.
    """
    async with session_factory() as session:
        player_id = uuid.uuid4()
        player = Player(
            id=player_id,
            username=f"test_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="not-a-real-hash",
            balance_micro=0,
        )
        session.add(player)
        await session.commit()
        return player_id
    
@pytest_asyncio.fixture
async def funded_player_id(session_factory) -> uuid.UUID:
    """Create a player with starting balance, properly debited from treasury.

    Unlike test_player_id (which has 0 balance), this player has funds
    and the treasury is debited — conservation invariant maintained.
    """
    from app.models.ledger import AccountEntityType, EntryType
    from app.services.transfer import transfer

    async with session_factory() as session:
        player_id = uuid.uuid4()
        player = Player(
            id=player_id,
            username=f"funded_{uuid.uuid4().hex[:8]}",
            email=f"funded_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="not-a-real-hash",
            balance_micro=0,
        )
        session.add(player)
        await session.flush()

        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id = result.scalar_one()

        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM,
            from_id=treasury_id,
            to_type=AccountEntityType.PLAYER,
            to_id=player_id,
            amount=settings.starting_balance_micro,
            entry_type=EntryType.STARTING_GRANT,
            memo="Test funded player",
        )
        await session.commit()
        return player_id