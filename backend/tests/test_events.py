"""Tests for the stochastic event engine."""

import pytest
from datetime import UTC, datetime

from sqlalchemy import select, func

from app.config import settings
from app.models.event import Event, EventType
from app.models.gate import Gate, GateRank, GateShare, GateStatus, DiscoveryType
from app.models.player import Player
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.services.event_engine import (
    roll_events,
    _handle_stability_surge,
    _handle_stability_crisis,
    _handle_yield_boom,
    _handle_market_shock,
    _handle_discovery_surge,
)
from app.simulation.rng import TickRNG


async def _setup(db, tick_number=1):
    tick = Tick(tick_number=tick_number, seed=42, started_at=datetime.now(UTC))
    db.add(tick)
    await db.flush()
    result = await db.execute(
        select(SystemAccount.id).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury_id = result.scalar_one()
    return tick, treasury_id


async def _make_gate(db, status=GateStatus.ACTIVE, stability=80.0,
                     rank=GateRank.E, base_yield_micro=5000, total_shares=100):
    gate = Gate(
        rank=rank, stability=stability, volatility=0.05,
        base_yield_micro=base_yield_micro, total_shares=total_shares,
        status=status, spawned_at_tick=0,
        discovery_type=DiscoveryType.SYSTEM,
    )
    db.add(gate)
    await db.flush()
    return gate


@pytest.mark.asyncio
async def test_event_fires_when_probability_passes(db, funded_player_id):
    tick, treasury_id = await _setup(db)
    gate = await _make_gate(db)
    db.add(GateShare(gate_id=gate.id, player_id=funded_player_id, quantity=50))
    db.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=50))
    await db.flush()

    rng = TickRNG(42)
    old = settings.event_probability
    settings.event_probability = 1.0
    try:
        events = await roll_events(db, tick.tick_number, tick.id, rng, treasury_id)
    finally:
        settings.event_probability = old

    assert len(events) == 1
    assert isinstance(events[0], Event)


@pytest.mark.asyncio
async def test_event_skipped_when_probability_zero(db):
    tick, treasury_id = await _setup(db)
    rng = TickRNG(42)

    old = settings.event_probability
    settings.event_probability = 0.0
    try:
        events = await roll_events(db, tick.tick_number, tick.id, rng, treasury_id)
    finally:
        settings.event_probability = old

    assert len(events) == 0


@pytest.mark.asyncio
async def test_stability_surge_increases_capped(db):
    tick, treasury_id = await _setup(db)
    gate = await _make_gate(db, stability=50.0)
    rng = TickRNG(99)

    event = await _handle_stability_surge(db, tick.tick_number, tick.id, rng, treasury_id)

    assert event is not None
    assert event.event_type == EventType.STABILITY_SURGE
    assert gate.stability > 50.0
    assert gate.stability <= 100.0  # E rank stability_init cap


@pytest.mark.asyncio
async def test_stability_crisis_decreases_floored(db):
    tick, treasury_id = await _setup(db)
    gate = await _make_gate(db, stability=80.0)
    rng = TickRNG(99)

    event = await _handle_stability_crisis(db, tick.tick_number, tick.id, rng, treasury_id)

    assert event is not None
    assert event.event_type == EventType.STABILITY_CRISIS
    assert gate.stability < 80.0
    assert gate.stability >= 0.0


@pytest.mark.asyncio
async def test_yield_boom_distributes_bonus(db, funded_player_id):
    tick, treasury_id = await _setup(db)
    gate = await _make_gate(db, base_yield_micro=10_000, stability=100.0)
    db.add(GateShare(gate_id=gate.id, player_id=funded_player_id, quantity=100))
    await db.flush()

    result = await db.execute(select(Player).where(Player.id == funded_player_id))
    player = result.scalar_one()
    balance_before = player.balance_micro

    rng = TickRNG(99)
    event = await _handle_yield_boom(db, tick.tick_number, tick.id, rng, treasury_id)

    assert event is not None
    assert event.event_type == EventType.YIELD_BOOM
    assert player.balance_micro > balance_before


@pytest.mark.asyncio
async def test_market_shock_decreases_all_stability(db):
    tick, treasury_id = await _setup(db)
    gate1 = await _make_gate(db, stability=80.0)
    gate2 = await _make_gate(db, stability=60.0)
    rng = TickRNG(99)

    event = await _handle_market_shock(db, tick.tick_number, tick.id, rng, treasury_id)

    assert event is not None
    assert event.event_type == EventType.MARKET_SHOCK
    assert gate1.stability < 80.0
    assert gate2.stability < 60.0
    assert gate1.stability >= 0.0
    assert gate2.stability >= 0.0


@pytest.mark.asyncio
async def test_discovery_surge_spawns_gates(db):
    tick, treasury_id = await _setup(db)
    rng = TickRNG(99)

    result = await db.execute(select(func.count(Gate.id)))
    before = result.scalar_one()

    event = await _handle_discovery_surge(db, tick.tick_number, tick.id, rng, treasury_id)

    assert event is not None
    assert event.event_type == EventType.DISCOVERY_SURGE

    result = await db.execute(select(func.count(Gate.id)))
    after = result.scalar_one()
    assert after > before
    assert event.payload["count"] >= 1 # type: ignore


@pytest.mark.asyncio
async def test_event_skipped_no_valid_targets(db):
    """Handler returns None when no ACTIVE/UNSTABLE gates exist."""
    tick, treasury_id = await _setup(db)
    rng = TickRNG(99)

    event = await _handle_stability_surge(db, tick.tick_number, tick.id, rng, treasury_id)
    assert event is None


@pytest.mark.asyncio
async def test_yield_boom_conservation(db, funded_player_id):
    tick, treasury_id = await _setup(db)
    gate = await _make_gate(db, base_yield_micro=10_000, stability=100.0)
    db.add(GateShare(gate_id=gate.id, player_id=funded_player_id, quantity=100))
    await db.flush()

    rng = TickRNG(99)
    await _handle_yield_boom(db, tick.tick_number, tick.id, rng, treasury_id)
    await db.flush()

    result = await db.execute(
        select(SystemAccount).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury = result.scalar_one()

    result = await db.execute(
        select(func.coalesce(func.sum(Player.balance_micro), 0))
    )
    player_sum = result.scalar_one()

    assert treasury.balance_micro + player_sum == settings.initial_seed_micro