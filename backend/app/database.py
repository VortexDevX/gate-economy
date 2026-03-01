from redis.asyncio import ConnectionPool, Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# ── Lazy singletons ──
_engine = None
_session_factory = None
_redis_pool = None


def get_engine():
    """Return the async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    """Return the async session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


def get_redis_pool():
    """Return the Redis connection pool, creating it on first call."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _redis_pool


def get_redis_client() -> Redis:
    """Return a Redis client backed by the shared connection pool."""
    return Redis(connection_pool=get_redis_pool())