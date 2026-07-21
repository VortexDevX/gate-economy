import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventType
from app.models.tick import Tick


@pytest.mark.asyncio
async def test_list_events_empty(client):
    resp = await client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def _seed_event(session: AsyncSession, event_type: EventType) -> Event:
    event = Event(
        event_type=event_type,
        tick_id=1,
        target_id=uuid.uuid4(),
        payload={"k": "v"},
    )
    session.add(event)
    await session.flush()
    return event


@pytest.mark.asyncio
async def test_list_events_returns_items(client, session_factory):
    async with session_factory() as session:
        await _seed_event(session, EventType.MARKET_SHOCK)
        await session.commit()

    resp = await client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["event_type"] == "MARKET_SHOCK"


@pytest.mark.asyncio
async def test_list_events_filter_by_type(client, session_factory):
    async with session_factory() as session:
        await _seed_event(session, EventType.MARKET_SHOCK)
        await _seed_event(session, EventType.YIELD_BOOM)
        await session.commit()

    resp = await client.get("/events", params={"event_type": "YIELD_BOOM"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "YIELD_BOOM"


@pytest.mark.asyncio
async def test_list_events_exposes_logical_tick_number(client, session_factory):
    async with session_factory() as session:
        tick = Tick(tick_number=91, seed=7, started_at=datetime.now(UTC))
        session.add(tick)
        await session.flush()
        session.add(Event(
            event_type=EventType.MARKET_SHOCK,
            tick_id=tick.id,
            target_id=uuid.uuid4(),
            payload={"k": "v"},
        ))
        await session.commit()

    resp = await client.get("/events")

    assert resp.status_code == 200
    assert resp.json()["items"][0]["tick_number"] == 91
