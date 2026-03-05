"""Tests for guild API endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.gate import DiscoveryType, Gate, GateRank, GateStatus
from app.models.guild import DividendPolicy, Guild, GuildGateHolding, GuildMember, GuildRole, GuildShare
from app.models.player import Player


@pytest_asyncio.fixture
async def seeded_guild(session_factory) -> uuid.UUID:
    """Create one guild with member, holdings, and shareholders for API tests."""
    async with session_factory() as session:
        founder = Player(
            id=uuid.uuid4(),
            username=f"guild_api_{uuid.uuid4().hex[:8]}",
            email=f"guild_api_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="not-a-real-hash",
            balance_micro=0,
        )
        shareholder = Player(
            id=uuid.uuid4(),
            username=f"guild_sh_{uuid.uuid4().hex[:8]}",
            email=f"guild_sh_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="not-a-real-hash",
            balance_micro=0,
        )
        session.add_all([founder, shareholder])
        await session.flush()

        gate = Gate(
            rank=GateRank.E,
            stability=90.0,
            volatility=0.0,
            base_yield_micro=1_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()

        guild = Guild(
            name="ApiGuild",
            founder_id=founder.id,
            treasury_micro=12_345,
            total_shares=1_000,
            public_float_pct=0.20,
            dividend_policy=DividendPolicy.MANUAL,
            auto_dividend_pct=None,
            status="ACTIVE",
            created_at_tick=1,
            maintenance_cost_micro=100_000,
            missed_maintenance_ticks=0,
            insolvent_ticks=0,
        )
        session.add(guild)
        await session.flush()

        session.add(
            GuildMember(
                guild_id=guild.id,
                player_id=founder.id,
                role=GuildRole.LEADER,
                joined_at_tick=1,
            )
        )
        session.add(GuildGateHolding(guild_id=guild.id, gate_id=gate.id, quantity=7))
        session.add_all(
            [
                GuildShare(guild_id=guild.id, player_id=founder.id, quantity=800),
                GuildShare(guild_id=guild.id, player_id=shareholder.id, quantity=150),
                GuildShare(guild_id=guild.id, player_id=guild.id, quantity=50),
            ]
        )

        await session.commit()
        return guild.id


@pytest.mark.asyncio
async def test_list_guilds_empty(client: AsyncClient):
    resp = await client.get("/guilds")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["guilds"], list)
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_list_guilds_returns_seeded(client: AsyncClient, seeded_guild: uuid.UUID):
    resp = await client.get("/guilds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    ids = [g["id"] for g in data["guilds"]]
    assert str(seeded_guild) in ids


@pytest.mark.asyncio
async def test_list_guilds_filter_by_status(client: AsyncClient, seeded_guild: uuid.UUID):
    resp = await client.get("/guilds", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    data = resp.json()
    for guild in data["guilds"]:
        assert guild["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_list_guilds_invalid_status_returns_400(client: AsyncClient):
    resp = await client.get("/guilds", params={"status": "INVALID"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_guild_detail_includes_members_holdings_shareholders(
    client: AsyncClient, seeded_guild: uuid.UUID
):
    resp = await client.get(f"/guilds/{seeded_guild}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(seeded_guild)
    assert data["name"] == "ApiGuild"
    assert data["status"] == "ACTIVE"
    assert data["shareholder_count"] == 2  # founder + external shareholder, excludes guild self-hold
    assert len(data["members"]) == 1
    assert data["members"][0]["role"] == "LEADER"
    assert len(data["gate_holdings"]) == 1
    assert data["gate_holdings"][0]["quantity"] == 7


@pytest.mark.asyncio
async def test_get_guild_not_found(client: AsyncClient):
    resp = await client.get(f"/guilds/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_guilds_pagination(client: AsyncClient, seeded_guild: uuid.UUID):
    resp = await client.get("/guilds", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["guilds"]) <= 1
    assert data["total"] >= 1
