from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.deps import get_db
from app.main import app
from app.models.treasury import AccountType, SystemAccount


def _make_engine():
    return create_async_engine(settings.database_url, poolclass=NullPool)


def _make_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_treasury(factory) -> None:
    async with factory() as session:
        result = await session.execute(
            select(SystemAccount).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(
                SystemAccount(
                    account_type=AccountType.TREASURY,
                    balance_micro=settings.initial_seed_micro,
                )
            )
            await session.commit()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Self-contained DB session for service-level tests."""
    engine = _make_engine()
    factory = _make_factory(engine)
    await _ensure_treasury(factory)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Self-contained HTTPX client with its own engine."""
    engine = _make_engine()
    factory = _make_factory(engine)
    await _ensure_treasury(factory)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()