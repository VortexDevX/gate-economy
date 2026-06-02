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


async def _stream_realtime(websocket: WebSocket) -> None:
    global _active_ws_connections
    await websocket.accept(subprotocol="dge.auth")
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
    """Authenticated websocket endpoint using token subprotocol."""
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    protocol_parts = [part.strip() for part in protocols.split(",")]
    token = (
        protocol_parts[1]
        if len(protocol_parts) >= 2 and protocol_parts[0] == "dge.auth"
        else None
    )
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

    try:
        player_id = uuid.UUID(sub)
    except (TypeError, ValueError):
        await websocket.close(code=1008, reason="Invalid token payload")
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Player.id).where(Player.id == player_id)
        )
        if result.scalar_one_or_none() is None:
            await websocket.close(code=1008, reason="Player not found")
            return

    await _stream_realtime(websocket)
