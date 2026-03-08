"""WebSocket endpoint — pushes real-time tick updates to connected clients."""

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select

from app.config import settings
from app.core.auth import decode_token
from app.database import get_session_factory
from app.models.player import Player

router = APIRouter(tags=["websocket"])
_active_ws_connections = 0


def get_active_ws_connections() -> int:
    """Expose current websocket connection count for metrics."""
    return _active_ws_connections


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    global _active_ws_connections
    await websocket.accept()
    _active_ws_connections += 1
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("dge:realtime")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        _active_ws_connections = max(0, _active_ws_connections - 1)
        await pubsub.unsubscribe("dge:realtime")
        await pubsub.aclose()
        await r.aclose()


@router.websocket("/ws/feed")
async def websocket_feed_endpoint(websocket: WebSocket) -> None:
    """Authenticated websocket endpoint using ?token=<access_jwt>."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008, reason="Invalid token type")
            return
        sub = payload.get("sub")
        if sub is None:
            await websocket.close(code=1008, reason="Invalid token payload")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Player.id).where(Player.id == uuid.UUID(sub))
        )
        if result.scalar_one_or_none() is None:
            await websocket.close(code=1008, reason="Player not found")
            return

    await websocket_endpoint(websocket)
