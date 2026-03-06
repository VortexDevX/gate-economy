"""Tests for news generation and the news API."""

import uuid

import pytest
from datetime import UTC, datetime

from app.config import settings
from app.models.event import Event, EventType
from app.models.gate import Gate, GateRank, GateStatus, DiscoveryType
from app.models.market import Trade, AssetType
from app.models.news import News, NewsCategory
from app.models.tick import Tick
from app.services.news_generator import generate_tick_news


async def _setup(db, tick_number=1):
    tick = Tick(tick_number=tick_number, seed=42, started_at=datetime.now(UTC))
    db.add(tick)
    await db.flush()
    return tick


# ── News generation tests ──


@pytest.mark.asyncio
async def test_news_generated_for_event(db):
    tick = await _setup(db)

    event = Event(
        event_type=EventType.MARKET_SHOCK,
        tick_id=tick.id,
        target_id=None,
        payload={"change": 3.5, "affected_count": 5},
    )
    db.add(event)
    await db.flush()

    news_items = await generate_tick_news(db, tick.tick_number, tick.id, [event])

    event_news = [n for n in news_items if "Market shock" in n.headline]
    assert len(event_news) == 1
    assert event_news[0].importance == 4
    assert event_news[0].category == NewsCategory.WORLD


@pytest.mark.asyncio
async def test_news_generated_for_gate_spawn(db):
    tick = await _setup(db)

    gate = Gate(
        rank=GateRank.S, stability=75.0, volatility=0.25,
        base_yield_micro=120_000, total_shares=30,
        status=GateStatus.OFFERING, spawned_at_tick=tick.tick_number,
        discovery_type=DiscoveryType.SYSTEM,
    )
    db.add(gate)
    await db.flush()

    news_items = await generate_tick_news(db, tick.tick_number, tick.id, [])

    spawn_news = [n for n in news_items if "appeared" in n.headline]
    assert len(spawn_news) == 1
    assert "Rank-S" in spawn_news[0].headline
    assert spawn_news[0].importance == 4  # S rank


@pytest.mark.asyncio
async def test_news_generated_for_gate_collapse(db):
    tick = await _setup(db, tick_number=5)

    gate = Gate(
        rank=GateRank.A, stability=0.0, volatility=0.20,
        base_yield_micro=50_000, total_shares=40,
        status=GateStatus.COLLAPSED, spawned_at_tick=1,
        collapsed_at_tick=5, discovery_type=DiscoveryType.SYSTEM,
    )
    db.add(gate)
    await db.flush()

    news_items = await generate_tick_news(db, tick.tick_number, tick.id, [])

    collapse_news = [n for n in news_items if "collapsed" in n.headline]
    assert len(collapse_news) == 1
    assert collapse_news[0].importance >= 3


@pytest.mark.asyncio
async def test_news_generated_for_large_trade(db):
    tick = await _setup(db)

    trade = Trade(
        buy_order_id=uuid.uuid4(), sell_order_id=uuid.uuid4(),
        asset_type=AssetType.GATE_SHARE, asset_id=uuid.uuid4(),
        quantity=10, price_micro=200_000,
        buyer_fee_micro=1000, seller_fee_micro=1000,
        tick_id=tick.id,
    )
    db.add(trade)
    await db.flush()

    news_items = await generate_tick_news(db, tick.tick_number, tick.id, [])

    trade_news = [n for n in news_items if "Large trade" in n.headline]
    assert len(trade_news) == 1
    assert trade_news[0].category == NewsCategory.MARKET


@pytest.mark.asyncio
async def test_no_news_for_small_trade(db):
    tick = await _setup(db)

    trade = Trade(
        buy_order_id=uuid.uuid4(), sell_order_id=uuid.uuid4(),
        asset_type=AssetType.GATE_SHARE, asset_id=uuid.uuid4(),
        quantity=1, price_micro=100,
        buyer_fee_micro=1, seller_fee_micro=1,
        tick_id=tick.id,
    )
    db.add(trade)
    await db.flush()

    news_items = await generate_tick_news(db, tick.tick_number, tick.id, [])

    trade_news = [n for n in news_items if "Large trade" in n.headline]
    assert len(trade_news) == 0


# ── News API tests ──


@pytest.mark.asyncio
async def test_news_api_paginated(client, session_factory):
    async with session_factory() as session:
        for i in range(5):
            session.add(News(
                tick_id=1, headline=f"Test news {i}",
                category=NewsCategory.GATE, importance=2,
            ))
        await session.commit()

    resp = await client.get("/news", params={"limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["limit"] == 3


@pytest.mark.asyncio
async def test_news_api_filter_category(client, session_factory):
    async with session_factory() as session:
        session.add(News(tick_id=1, headline="Gate news",
                         category=NewsCategory.GATE, importance=2))
        session.add(News(tick_id=1, headline="Market news",
                         category=NewsCategory.MARKET, importance=2))
        await session.commit()

    resp = await client.get("/news", params={"category": "GATE"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "GATE"


@pytest.mark.asyncio
async def test_news_api_filter_importance(client, session_factory):
    async with session_factory() as session:
        session.add(News(tick_id=1, headline="Minor",
                         category=NewsCategory.GATE, importance=1))
        session.add(News(tick_id=1, headline="Major",
                         category=NewsCategory.GATE, importance=4))
        await session.commit()

    resp = await client.get("/news", params={"min_importance": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["headline"] == "Major"