import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.database import get_redis_client, get_session_factory
from app.models.player import Player

_bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session, auto-closed on exit."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield a Redis client from the shared pool, returned on exit."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Player:
    """Extract and validate JWT, return the authenticated Player."""
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    player_id = payload.get("sub")
    if player_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(
        select(Player).where(Player.id == uuid.UUID(player_id))
    )
    player = result.scalar_one_or_none()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Player not found",
        )

    return player


# ── Type aliases for dependency injection ──
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentPlayer = Annotated[Player, Depends(get_current_player)]