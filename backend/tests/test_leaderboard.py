"""Tests for leaderboard & seasons (Phase 10)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateRank, GateShare, GateStatus
from app.models.guild import Guild, GuildShare, GuildStatus, DividendPolicy
from app.models.leaderboard import (
    PlayerNetWorth,
    Season,
    SeasonResult,
    SeasonStatus,
)
from app.models.market import AssetType, MarketPrice
from app.models.player import Player
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.services.leaderboard import (
    _apply_decay,
    check_season,
    update_leaderboard,
)


# ── Helpers ──


async def _make_tick(session: AsyncSession, tick_number: int) -> Tick:
    from datetime import UTC, datetime

    tick = Tick(tick_number=tick_number, seed=42, started_at=datetime.now(UTC))
    session.add(tick)
    await session.flush()
    return tick


async def _make_gate(
    session, status=GateStatus.ACTIVE, stability=80.0,
    base_yield_micro=5_000, total_shares=100,
):
    gate = Gate(
        id=uuid.uuid4(), rank=GateRank.E, stability=stability,
        volatility=0.05, base_yield_micro=base_yield_micro,
        total_shares=total_shares, status=status,
        spawned_at_tick=1, discovery_type="SYSTEM",
    )
    session.add(gate)
    await session.flush()
    return gate


async def _give_shares(session, gate_id, player_id, quantity):
    session.add(GateShare(gate_id=gate_id, player_id=player_id, quantity=quantity))
    await session.flush()


async def _set_market_price(session, asset_type, asset_id, price, tick=1):
    session.add(MarketPrice(
        asset_type=asset_type, asset_id=asset_id,
        last_price_micro=price, updated_at_tick=tick,
    ))
    await session.flush()


async def _get_treasury_id(session):
    result = await session.execute(
        select(SystemAccount.id).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    return result.scalar_one()


async def _create_funded_player(session, balance=None, username=None, is_ai=False):
    """Create a player with proper treasury debit. Returns the Player object."""
    from app.models.ledger import AccountEntityType, EntryType
    from app.services.transfer import transfer

    if balance is None:
        balance = settings.starting_balance_micro
    if username is None:
        username = f"p_{uuid.uuid4().hex[:8]}"
    treasury_id = await _get_treasury_id(session)
    player = Player(
        id=uuid.uuid4(), username=username,
        email=f"{username}@test.com", password_hash="x",
        balance_micro=0, is_ai=is_ai,
    )
    session.add(player)
    await session.flush()
    await transfer(
        session=session, from_type=AccountEntityType.SYSTEM,
        from_id=treasury_id, to_type=AccountEntityType.PLAYER,
        to_id=player.id, amount=balance,
        entry_type=EntryType.AI_BUDGET if is_ai else EntryType.STARTING_GRANT,
        memo=f"test: {username}",
    )
    return player


# ── Net Worth Computation ──


@pytest.mark.asyncio
async def test_balance_only_net_worth(db, funded_player_id):
    tick = await _make_tick(db, 12)
    await update_leaderboard(db, 12, tick.id)
    result = await db.execute(
        select(PlayerNetWorth).where(PlayerNetWorth.player_id == funded_player_id)
    )
    pnw = result.scalar_one()
    assert pnw.net_worth_micro == settings.starting_balance_micro
    assert pnw.portfolio_micro == 0
    assert pnw.balance_micro == settings.starting_balance_micro


@pytest.mark.asyncio
async def test_gate_shares_market_price(db, funded_player_id):
    gate = await _make_gate(db)
    await _give_shares(db, gate.id, funded_player_id, 10)
    await _set_market_price(db, AssetType.GATE_SHARE, gate.id, 50_000)
    tick = await _make_tick(db, 12)
    await update_leaderboard(db, 12, tick.id)
    result = await db.execute(
        select(PlayerNetWorth).where(PlayerNetWorth.player_id == funded_player_id)
    )
    pnw = result.scalar_one()
    assert pnw.portfolio_micro == 10 * 50_000
    assert pnw.net_worth_micro == settings.starting_balance_micro + 500_000


@pytest.mark.asyncio
async def test_gate_shares_fundamental_fallback(db, funded_player_id):
    gate = await _make_gate(db, stability=80.0, base_yield_micro=5_000, total_shares=100)
    await _give_shares(db, gate.id, funded_player_id, 10)
    tick = await _make_tick(db, 12)
    await update_leaderboard(db, 12, tick.id)
    result = await db.execute(
        select(PlayerNetWorth).where(PlayerNetWorth.player_id == funded_player_id)
    )
    pnw = result.scalar_one()
    expected = int(5_000 * (80.0 / 100.0) * settings.iso_payback_ticks) // 100
    assert pnw.portfolio_micro == 10 * expected


@pytest.mark.asyncio
async def test_guild_shares_in_portfolio(db, funded_player_id):
    guild = Guild(
        id=uuid.uuid4(), name="TestGuild", founder_id=funded_player_id,
        treasury_micro=0, total_shares=1000, public_float_pct=0.49,
        dividend_policy=DividendPolicy.MANUAL, status=GuildStatus.ACTIVE,
        created_at_tick=1, maintenance_cost_micro=100_000,
    )
    db.add(guild)
    await db.flush()
    db.add(GuildShare(guild_id=guild.id, player_id=funded_player_id, quantity=100))
    await db.flush()
    tick = await _make_tick(db, 12)
    await update_leaderboard(db, 12, tick.id)
    result = await db.execute(
        select(PlayerNetWorth).where(PlayerNetWorth.player_id == funded_player_id)
    )
    pnw = result.scalar_one()
    fallback = settings.guild_creation_cost_micro // settings.guild_total_shares
    assert pnw.portfolio_micro == 100 * fallback


@pytest.mark.asyncio
async def test_collapsed_gate_excluded(db, funded_player_id):
    gate = await _make_gate(db, status=GateStatus.COLLAPSED)
    await _give_shares(db, gate.id, funded_player_id, 50)
    tick = await _make_tick(db, 12)
    await update_leaderboard(db, 12, tick.id)
    result = await db.execute(
        select(PlayerNetWorth).where(PlayerNetWorth.player_id == funded_player_id)
    )
    pnw = result.scalar_one()
    assert pnw.portfolio_micro == 0


# ── Decay ──


@pytest.mark.asyncio
async def test_active_player_no_decay():
    score = _apply_decay(1_000_000, tick_number=50, last_active_tick=40)
    assert score == 1_000_000


@pytest.mark.asyncio
async def test_inactive_player_decay_applied():
    score = _apply_decay(1_000_000, tick_number=200, last_active_tick=0)
    # inactive = 200 - 0 - 100 = 100; mult = max(0.50, 1.0 - 0.0001*100) = 0.99
    assert score == 990_000
    assert score < 1_000_000


@pytest.mark.asyncio
async def test_decay_floors_at_minimum():
    score = _apply_decay(1_000_000, tick_number=10_000, last_active_tick=0)
    assert score == int(1_000_000 * settings.leaderboard_decay_floor)


# ── Season Management ──


@pytest.mark.asyncio
async def test_first_season_created(db):
    tick = await _make_tick(db, 1)
    await check_season(db, 1, tick.id)
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.ACTIVE)
    )
    season = result.scalar_one()
    assert season.season_number == 1
    assert season.start_tick == 1


@pytest.mark.asyncio
async def test_season_completes_on_duration(db, funded_player_id):
    tick1 = await _make_tick(db, 1)
    await check_season(db, 1, tick1.id)
    await db.flush()

    end_tick = 1 + settings.season_duration_ticks
    tick2 = await _make_tick(db, end_tick)
    await check_season(db, end_tick, tick2.id)
    await db.flush()

    result = await db.execute(select(Season).order_by(Season.season_number))
    seasons = list(result.scalars().all())
    assert len(seasons) == 2
    assert seasons[0].status == SeasonStatus.COMPLETED
    assert seasons[0].end_tick == end_tick
    assert seasons[1].status == SeasonStatus.ACTIVE
    assert seasons[1].season_number == 2


@pytest.mark.asyncio
async def test_season_results_recorded(db, funded_player_id):
    tick1 = await _make_tick(db, 1)
    await check_season(db, 1, tick1.id)
    await db.flush()

    player2 = await _create_funded_player(db, balance=5_000_000)

    end_tick = 1 + settings.season_duration_ticks
    tick2 = await _make_tick(db, end_tick)
    await check_season(db, end_tick, tick2.id)
    await db.flush()

    # Query completed season dynamically (SERIAL id is not reset between tests)
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.COMPLETED)
    )
    completed = result.scalar_one()

    result = await db.execute(
        select(SeasonResult)
        .where(SeasonResult.season_id == completed.id)
        .order_by(SeasonResult.final_rank)
    )
    results = list(result.scalars().all())
    assert len(results) == 2
    assert results[0].final_rank == 1
    assert results[1].final_rank == 2
    assert results[0].final_score_micro >= results[1].final_score_micro


@pytest.mark.asyncio
async def test_new_season_starts_after_completion(db):
    tick1 = await _make_tick(db, 1)
    await check_season(db, 1, tick1.id)
    await db.flush()

    end_tick = 1 + settings.season_duration_ticks
    tick2 = await _make_tick(db, end_tick)
    await check_season(db, end_tick, tick2.id)
    await db.flush()

    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.ACTIVE)
    )
    active = result.scalar_one()
    assert active.season_number == 2
    assert active.start_tick == end_tick


# ── API ──


@pytest.mark.asyncio
async def test_leaderboard_api_paginated(client, session_factory):
    async with session_factory() as session:
        player = await _create_funded_player(session, username="lb_user1")
        session.add(PlayerNetWorth(
            player_id=player.id,
            net_worth_micro=settings.starting_balance_micro,
            score_micro=settings.starting_balance_micro,
            balance_micro=settings.starting_balance_micro,
            portfolio_micro=0, updated_at_tick=1,
        ))
        await session.commit()

    resp = await client.get("/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["entries"][0]["rank"] == 1
    assert data["entries"][0]["username"] == "lb_user1"


@pytest.mark.asyncio
async def test_leaderboard_excludes_ai(client, session_factory):
    async with session_factory() as session:
        ai = await _create_funded_player(
            session, balance=1_000_000, username="ai_bot", is_ai=True,
        )
        human = await _create_funded_player(session, username="human1")

        for p in [ai, human]:
            session.add(PlayerNetWorth(
                player_id=p.id, net_worth_micro=p.balance_micro,
                score_micro=p.balance_micro, balance_micro=p.balance_micro,
                portfolio_micro=0, updated_at_tick=1,
            ))
        await session.commit()

    resp = await client.get("/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    usernames = [e["username"] for e in data["entries"]]
    assert "ai_bot" not in usernames
    assert "human1" in usernames


@pytest.mark.asyncio
async def test_leaderboard_me(client, session_factory):
    reg = await client.post("/auth/register", json={
        "username": "me_user", "email": "me@test.com", "password": "testpass123",
    })
    assert reg.status_code == 201
    login = await client.post("/auth/login", json={
        "email": "me@test.com", "password": "testpass123",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    me_resp = await client.get(
        "/players/me", headers={"Authorization": f"Bearer {token}"},
    )
    player_id = uuid.UUID(me_resp.json()["id"])

    async with session_factory() as session:
        session.add(PlayerNetWorth(
            player_id=player_id,
            net_worth_micro=settings.starting_balance_micro,
            score_micro=settings.starting_balance_micro,
            balance_micro=settings.starting_balance_micro,
            portfolio_micro=0, last_active_tick=0, updated_at_tick=12,
        ))
        await session.commit()

    resp = await client.get(
        "/leaderboard/me", headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rank"] == 1
    assert data["score_micro"] > 0


@pytest.mark.asyncio
async def test_leaderboard_me_no_data(client):
    reg = await client.post("/auth/register", json={
        "username": "new_user", "email": "new@test.com", "password": "testpass123",
    })
    assert reg.status_code == 201
    login = await client.post("/auth/login", json={
        "email": "new@test.com", "password": "testpass123",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    resp = await client.get(
        "/leaderboard/me", headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rank"] is None
    assert data["score_micro"] == 0


@pytest.mark.asyncio
async def test_seasons_api(client, session_factory):
    async with session_factory() as session:
        session.add(Season(
            season_number=1, start_tick=1, status=SeasonStatus.ACTIVE,
        ))
        await session.commit()

    resp = await client.get("/seasons")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["season_number"] == 1


@pytest.mark.asyncio
async def test_current_season_api(client, session_factory):
    async with session_factory() as session:
        session.add(Season(
            season_number=1, start_tick=1, status=SeasonStatus.ACTIVE,
        ))
        await session.commit()

    resp = await client.get("/seasons/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["season_number"] == 1


@pytest.mark.asyncio
async def test_current_season_404_when_none(client):
    resp = await client.get("/seasons/current")
    assert resp.status_code == 404


# ── Integration ──


@pytest.mark.asyncio
async def test_full_tick_with_leaderboard(session_factory, funded_player_id):
    orig_spawn = settings.system_spawn_probability
    orig_event = settings.event_probability
    orig_interval = settings.net_worth_update_interval
    settings.system_spawn_probability = 0.0
    settings.event_probability = 0.0
    settings.net_worth_update_interval = 1
    try:
        from app.simulation.tick import execute_tick

        tick = await execute_tick(session_factory)
        assert tick.tick_number == 1
        assert tick.state_hash is not None

        async with session_factory() as session:
            result = await session.execute(
                select(Season).where(Season.status == SeasonStatus.ACTIVE)
            )
            season = result.scalar_one()
            assert season.season_number == 1

            result = await session.execute(
                select(PlayerNetWorth).where(
                    PlayerNetWorth.player_id == funded_player_id
                )
            )
            pnw = result.scalar_one()
            assert pnw.net_worth_micro == settings.starting_balance_micro
    finally:
        settings.system_spawn_probability = orig_spawn
        settings.event_probability = orig_event
        settings.net_worth_update_interval = orig_interval
