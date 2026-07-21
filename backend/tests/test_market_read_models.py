"""HTTP coverage for player-facing market and portfolio projections."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.gate import DiscoveryType, Gate, GateRank, GateShare, GateStatus
from app.models.market import AssetType, MarketPrice, Order, OrderSide, Trade
from app.models.tick import Tick


async def _register_and_login(client) -> tuple[dict[str, str], uuid.UUID]:
    suffix = uuid.uuid4().hex[:8]
    email = f"portfolio_{suffix}@test.com"
    await client.post(
        "/auth/register",
        json={
            "username": f"portfolio_{suffix}",
            "email": email,
            "password": "securepass123",
        },
    )
    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/players/me", headers=headers)
    return headers, uuid.UUID(me.json()["id"])


@pytest.mark.asyncio
async def test_portfolio_returns_marked_positions_and_reserved_cash(
    client,
    session_factory,
):
    headers, player_id = await _register_and_login(client)
    async with session_factory() as session:
        tick = Tick(
            tick_number=7,
            seed=7,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(tick)
        gate = Gate(
            rank=GateRank.E,
            stability=80.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.PLAYER,
            discoverer_id=player_id,
        )
        session.add(gate)
        await session.flush()
        session.add_all(
            [
                GateShare(gate_id=gate.id, player_id=player_id, quantity=10),
                MarketPrice(
                    asset_type=AssetType.GATE_SHARE,
                    asset_id=gate.id,
                    last_price_micro=50_000,
                    best_bid_micro=48_000,
                    best_ask_micro=52_000,
                    volume_24h_micro=2_000_000,
                    updated_at_tick=7,
                ),
                Order(
                    player_id=player_id,
                    asset_type=AssetType.GATE_SHARE,
                    asset_id=gate.id,
                    side=OrderSide.BUY,
                    quantity=1,
                    price_limit_micro=1_000,
                    escrow_micro=1_234,
                    created_at_tick=7,
                ),
            ]
        )
        await session.commit()
        gate_id = gate.id

    response = await client.get("/players/me/portfolio", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["as_of_tick"] == 7
    assert data["reserved_cash_micro"] == 1_234
    assert data["gate_value_micro"] == 500_000
    assert data["projected_yield_per_tick_micro"] == 800
    assert data["net_worth_micro"] == 10_501_234
    assert len(data["gate_positions"]) == 1
    position = data["gate_positions"][0]
    assert position["gate_id"] == str(gate_id)
    assert position["ticker"].startswith("DG-E-")
    assert position["display_name"]
    assert position["risk_band"] == "STABLE"


@pytest.mark.asyncio
async def test_market_overview_exposes_edge_risk_and_liquidity(
    client,
    session_factory,
):
    async with session_factory() as session:
        gate = Gate(
            rank=GateRank.E,
            stability=80.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=5,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        session.add(
            Gate(
                rank=GateRank.E,
                stability=0.0,
                volatility=0.05,
                base_yield_micro=10_000,
                total_shares=100,
                status=GateStatus.COLLAPSED,
                spawned_at_tick=1,
                collapsed_at_tick=4,
                discovery_type=DiscoveryType.SYSTEM,
            )
        )
        await session.flush()
        session.add(
            MarketPrice(
                asset_type=AssetType.GATE_SHARE,
                asset_id=gate.id,
                last_price_micro=50_000,
                best_bid_micro=48_000,
                best_ask_micro=52_000,
                volume_24h_micro=2_000_000,
                updated_at_tick=7,
            )
        )
        await session.commit()
        gate_id = gate.id

    response = await client.get(
        "/market/overview",
        params={"sort_by": "YIELD", "status": "ACTIVE"},
    )
    assert response.status_code == 200
    data = response.json()
    item = next(row for row in data["items"] if row["asset_id"] == str(gate_id))
    assert item["effective_yield_micro"] == 8_000
    assert item["yield_per_share_micro"] == 80
    assert item["mark_price_micro"] == 50_000
    assert item["spread_bps"] == 800
    assert item["distance_to_instability"] == 60.0
    assert item["risk_band"] == "STABLE"
    assert data["active_count"] >= 1
    assert data["collapsed_count"] == 1


@pytest.mark.asyncio
async def test_market_history_aggregates_ohlc_per_logical_tick(
    client,
    session_factory,
):
    gate_id = uuid.uuid4()
    async with session_factory() as session:
        tick_10 = Tick(
            tick_number=10,
            seed=10,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        tick_11 = Tick(
            tick_number=11,
            seed=11,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add_all([tick_10, tick_11])
        await session.flush()
        session.add_all(
            [
                Trade(
                    buy_order_id=uuid.uuid4(),
                    sell_order_id=uuid.uuid4(),
                    asset_type=AssetType.GATE_SHARE,
                    asset_id=gate_id,
                    quantity=2,
                    price_micro=100,
                    buyer_fee_micro=1,
                    seller_fee_micro=1,
                    tick_id=tick_10.id,
                ),
                Trade(
                    buy_order_id=uuid.uuid4(),
                    sell_order_id=uuid.uuid4(),
                    asset_type=AssetType.GATE_SHARE,
                    asset_id=gate_id,
                    quantity=1,
                    price_micro=130,
                    buyer_fee_micro=1,
                    seller_fee_micro=1,
                    tick_id=tick_10.id,
                ),
                Trade(
                    buy_order_id=uuid.uuid4(),
                    sell_order_id=uuid.uuid4(),
                    asset_type=AssetType.GATE_SHARE,
                    asset_id=gate_id,
                    quantity=3,
                    price_micro=120,
                    buyer_fee_micro=1,
                    seller_fee_micro=1,
                    tick_id=tick_11.id,
                ),
            ]
        )
        await session.commit()

    response = await client.get(f"/market/GATE_SHARE/{gate_id}/history")
    assert response.status_code == 200
    points = response.json()["points"]
    assert [point["tick_number"] for point in points] == [10, 11]
    assert points[0]["open_micro"] == 100
    assert points[0]["high_micro"] == 130
    assert points[0]["low_micro"] == 100
    assert points[0]["close_micro"] == 130
    assert points[0]["average_price_micro"] == 110
    assert points[0]["volume_quantity"] == 3


@pytest.mark.asyncio
async def test_order_preview_uses_live_fee_and_position_availability(
    client,
    session_factory,
):
    headers, player_id = await _register_and_login(client)
    async with session_factory() as session:
        gate = Gate(
            rank=GateRank.E,
            stability=80.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(
            GateShare(gate_id=gate.id, player_id=player_id, quantity=10)
        )
        await session.commit()
        gate_id = gate.id

    buy = await client.post(
        "/market/order-preview",
        headers=headers,
        json={
            "asset_type": "GATE_SHARE",
            "asset_id": str(gate_id),
            "side": "BUY",
            "quantity": 5,
            "price_limit_micro": 50_000,
        },
    )
    assert buy.status_code == 200
    buy_data = buy.json()
    assert buy_data["gross_value_micro"] == 250_000
    assert buy_data["estimated_fee_micro"] == 4_375
    assert buy_data["required_escrow_micro"] == 254_375
    assert buy_data["can_submit"] is True

    sell = await client.post(
        "/market/order-preview",
        headers=headers,
        json={
            "asset_type": "GATE_SHARE",
            "asset_id": str(gate_id),
            "side": "SELL",
            "quantity": 11,
            "price_limit_micro": 50_000,
        },
    )
    assert sell.status_code == 200
    sell_data = sell.json()
    assert sell_data["available_shares"] == 10
    assert sell_data["can_submit"] is False
    assert "10 shares" in sell_data["reason"]
