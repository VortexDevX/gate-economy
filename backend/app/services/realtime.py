"""Realtime — publish tick updates via Redis pub/sub."""

import json

import structlog
from redis.asyncio import Redis

from app.config import settings
from app.models.news import News

logger = structlog.get_logger()


async def publish_tick_update(
    tick_number: int, news_items: list[News]
) -> None:
    """Publish tick summary to Redis pub/sub. Fire-and-forget."""
    payload = {
        "type": "tick_update",
        "tick_number": tick_number,
        "news": [
            {
                "id": str(n.id),
                "headline": n.headline,
                "category": n.category.value,
                "importance": n.importance,
            }
            for n in news_items
        ],
    }

    try:
        r = Redis.from_url(settings.redis_url, decode_responses=True)
        await r.publish("dge:realtime", json.dumps(payload))
        await r.aclose()
    except Exception:
        logger.warning("realtime_publish_failed", tick_number=tick_number)