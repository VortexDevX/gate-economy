from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session, auto-closed on exit."""
    async with async_session_factory() as session:
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield a Redis client from the shared pool, returned on exit."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
