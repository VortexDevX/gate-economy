from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Readiness probe — verifies DB and Redis connectivity."""
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready", "database": "ok", "redis": "ok"}
