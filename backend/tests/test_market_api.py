"""Market API endpoint tests.

Tests HTTP-level behavior: response shapes, status codes, filters.
Market logic is tested in test_market.py at the simulation level.
"""

import uuid

import pytest

from app.models.market import AssetType, MarketPrice, Order, OrderSide, OrderStatus, Trade


# ── Helpers ──


async def _register_and_login(client, username="trader", email="trader@test.com"):
    await client.post("/auth/register", json={
        "username": username, "email": email, "password": "testpass123",
    })
    resp = await client.post("/auth/login", json={
        "email": email, "password": "testpass123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _get_player_id(client, headers) -> uuid.UUID:
    resp = await client.get("/players/me", headers=headers)
    return uuid.UUID(resp.json()["id"])


# ── GET /orders/me ──


@pytest.mark.asyncio
async def test_orders_me_empty(client):
    """Authenticated player with no orders gets empty list."""
    headers = await _register_and_login(client)
    resp = await client.get("/orders/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_orders_me_with_orders(client, session_factory):
    """Returns only the authenticated player's orders."""
    headers = await _register_and_login(client)
    pid = await _get_player_id(client, headers)
    gate_id = uuid.uuid4()

    # Insert order directly — testing API response, not placement logic
    async with session_factory() as s:
        s.add(Order(
            player_id=pid,
            asset_type=AssetType.GATE_SHARE,
            asset_id=gate_id,
            side=OrderSide.BUY,
            quantity=10,
            price_limit_micro=50_000,
            escrow_micro=525_000,
            created_at_tick=1,
        ))
        # Another player's order — should NOT appear
        s.add(Order(
            player_id=uuid.uuid4(),
            asset_type=AssetType.GATE_SHARE,
            asset_id=gate_id,
            side=OrderSide.SELL,
            quantity=5,
            price_limit_micro=60_000,
            created_at_tick=1,
        ))
        await s.commit()

    resp = await client.get("/orders/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["orders"][0]["quantity"] == 10
    assert data["orders"][0]["side"] == "BUY"


# ── GET /market/{asset_type}/{asset_id} ──


@pytest.mark.asyncio
async def test_market_price(client, session_factory):
    """Returns price data for an asset with market history."""
    gate_id = uuid.uuid4()
    async with session_factory() as s:
        s.add(MarketPrice(
            asset_type=AssetType.GATE_SHARE,
            asset_id=gate_id,
            last_price_micro=50_000,
            best_bid_micro=48_000,
            best_ask_micro=52_000,
            volume_24h_micro=1_000_000,
            updated_at_tick=1,
        ))
        await s.commit()

    resp = await client.get(f"/market/GATE_SHARE/{gate_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_price_micro"] == 50_000
    assert data["best_bid_micro"] == 48_000
    assert data["best_ask_micro"] == 52_000
    assert data["volume_24h_micro"] == 1_000_000


@pytest.mark.asyncio
async def test_market_price_nonexistent(client):
    """Nonexistent asset returns 200 with null/default values (not 404)."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/market/GATE_SHARE/{fake_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_price_micro"] is None
    assert data["best_bid_micro"] is None
    assert data["best_ask_micro"] is None


# ── GET /market/{asset_type}/{asset_id}/book ──


@pytest.mark.asyncio
async def test_order_book(client, session_factory):
    """Aggregated order book shows bids descending, asks ascending."""
    gate_id = uuid.uuid4()
    async with session_factory() as s:
        s.add_all([
            Order(
                player_id=uuid.uuid4(), asset_type=AssetType.GATE_SHARE,
                asset_id=gate_id, side=OrderSide.BUY, quantity=10,
                price_limit_micro=50_000, created_at_tick=1,
            ),
            Order(
                player_id=uuid.uuid4(), asset_type=AssetType.GATE_SHARE,
                asset_id=gate_id, side=OrderSide.BUY, quantity=15,
                price_limit_micro=50_000, created_at_tick=2,
            ),
            Order(
                player_id=uuid.uuid4(), asset_type=AssetType.GATE_SHARE,
                asset_id=gate_id, side=OrderSide.SELL, quantity=5,
                price_limit_micro=55_000, created_at_tick=1,
            ),
        ])
        await s.commit()

    resp = await client.get(f"/market/GATE_SHARE/{gate_id}/book")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bids"]) == 1
    assert data["bids"][0]["price_micro"] == 50_000
    assert data["bids"][0]["total_quantity"] == 25
    assert data["bids"][0]["order_count"] == 2
    assert len(data["asks"]) == 1
    assert data["asks"][0]["price_micro"] == 55_000
    assert data["asks"][0]["total_quantity"] == 5


# ── GET /market/{asset_type}/{asset_id}/trades ──


@pytest.mark.asyncio
async def test_trades_list(client, session_factory):
    """Returns recent trades for an asset."""
    gate_id = uuid.uuid4()
    async with session_factory() as s:
        s.add(Trade(
            buy_order_id=uuid.uuid4(), sell_order_id=uuid.uuid4(),
            asset_type=AssetType.GATE_SHARE, asset_id=gate_id,
            quantity=5, price_micro=50_000,
            buyer_fee_micro=500, seller_fee_micro=500,
            tick_id=1,
        ))
        await s.commit()

    resp = await client.get(f"/market/GATE_SHARE/{gate_id}/trades")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["trades"][0]["quantity"] == 5
    assert data["trades"][0]["price_micro"] == 50_000


# ── Validation ──


@pytest.mark.asyncio
async def test_invalid_asset_type_422(client):
    """Invalid asset_type in path returns 422."""
    resp = await client.get(f"/market/INVALID_TYPE/{uuid.uuid4()}")
    assert resp.status_code == 422