"""Tests for gate API endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.gate import DiscoveryType, Gate, GateRank, GateShare, GateStatus


@pytest_asyncio.fixture
async def seeded_gate(session_factory) -> uuid.UUID:
    """Create a test gate directly in DB and return its ID."""
    async with session_factory() as session:
        from sqlalchemy import select
        from app.models.treasury import AccountType, SystemAccount

        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id = result.scalar_one()

        gate = Gate(
            rank=GateRank.E,
            stability=95.0,
            volatility=0.05,
            base_yield_micro=3000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(
            GateShare(gate_id=gate.id, player_id=treasury_id, quantity=100)
        )
        await session.commit()
        return gate.id


@pytest.mark.asyncio
async def test_list_gates_empty(client: AsyncClient):
    """GET /gates returns empty list when no gates exist."""
    resp = await client.get("/gates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 0
    assert isinstance(data["gates"], list)


@pytest.mark.asyncio
async def test_list_gates_returns_gate(client: AsyncClient, seeded_gate: uuid.UUID):
    """GET /gates includes seeded gate."""
    resp = await client.get("/gates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    gate_ids = [g["id"] for g in data["gates"]]
    assert str(seeded_gate) in gate_ids


@pytest.mark.asyncio
async def test_list_gates_filter_by_status(
    client: AsyncClient, seeded_gate: uuid.UUID
):
    """GET /gates?status=ACTIVE filters correctly."""
    resp = await client.get("/gates", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    data = resp.json()
    for gate in data["gates"]:
        assert gate["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_list_gates_invalid_status(client: AsyncClient):
    """GET /gates?status=INVALID returns 422."""
    resp = await client.get("/gates", params={"status": "INVALID"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_gate_detail(client: AsyncClient, seeded_gate: uuid.UUID):
    """GET /gates/{id} returns gate with shareholders."""
    resp = await client.get(f"/gates/{seeded_gate}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(seeded_gate)
    assert data["rank"] == "E"
    assert data["status"] == "ACTIVE"
    assert isinstance(data["shareholders"], list)
    assert len(data["shareholders"]) >= 1
    # Treasury holds 100% initially
    assert data["shareholders"][0]["quantity"] == 100
    assert data["shareholders"][0]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_gate_not_found(client: AsyncClient):
    """GET /gates/{invalid_id} returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/gates/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rank_profiles_returns_all(client: AsyncClient):
    """GET /gates/rank-profiles returns all 7 rank profiles."""
    resp = await client.get("/gates/rank-profiles")
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) == 7
    ranks = {p["rank"] for p in profiles}
    expected = {"E", "D", "C", "B", "A", "S", "S_PLUS"}
    assert ranks == expected