"""Tests for WebSocket / realtime publishing."""

import json

import pytest

from app.config import settings
from app.services.realtime import publish_tick_update


@pytest.mark.asyncio
async def test_publish_sends_to_redis(redis_client):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("dge:realtime")
    await pubsub.get_message(timeout=1.0)  # consume subscribe confirmation

    await publish_tick_update(42, [])

    msg = await pubsub.get_message(timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"
    data = json.loads(msg["data"])
    assert data["type"] == "tick_update"
    assert data["tick_number"] == 42
    assert data["news"] == []

    await pubsub.unsubscribe("dge:realtime")
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_tick_publishes_realtime_update(
    session_factory, pause_simulation, redis_client
):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("dge:realtime")
    await pubsub.get_message(timeout=1.0)  # consume subscribe confirmation

    old_spawn = settings.system_spawn_probability
    old_event = settings.event_probability
    settings.system_spawn_probability = 0.0
    settings.event_probability = 0.0
    try:
        from app.simulation.tick import execute_tick

        tick = await execute_tick(session_factory)
    finally:
        settings.system_spawn_probability = old_spawn
        settings.event_probability = old_event

    msg = await pubsub.get_message(timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"
    data = json.loads(msg["data"])
    assert data["type"] == "tick_update"
    assert data["tick_number"] == tick.tick_number

    await pubsub.unsubscribe("dge:realtime")
    await pubsub.aclose()