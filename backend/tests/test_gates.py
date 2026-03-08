"""Tests for gate lifecycle — spawn, discover, decay, yield, conservation."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import DiscoveryType, Gate, GateRank, GateShare, GateStatus
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.ledger import AccountEntityType, EntryType
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.gate_lifecycle import (
    advance_gate_lifecycle,
    distribute_yield,
    system_spawn_gate,
)
from app.services.transfer import transfer
from app.simulation.rng import TickRNG
from app.simulation.tick import execute_tick


# ── Helpers ──


async def _get_treasury(session: AsyncSession) -> SystemAccount:
    result = await session.execute(
        select(SystemAccount)
        .where(SystemAccount.account_type == AccountType.TREASURY)
        .with_for_update()
    )
    return result.scalar_one()


async def _get_treasury_id(session: AsyncSession) -> uuid.UUID:
    result = await session.execute(
        select(SystemAccount.id).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    return result.scalar_one()


async def _create_funded_player(
    session: AsyncSession, balance: int
) -> Player:
    """Create a player with a given balance (via treasury transfer for conservation)."""
    treasury = await _get_treasury(session)
    player = Player(
        id=uuid.uuid4(),
        username=f"test_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="not-a-real-hash",
        balance_micro=0,
    )
    session.add(player)
    await session.flush()

    if balance > 0:
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM,
            from_id=treasury.id,
            to_type=AccountEntityType.PLAYER,
            to_id=player.id,
            amount=balance,
            entry_type=EntryType.STARTING_GRANT,
            memo="Test funding",
        )

    return player


# ── System Spawn Tests ──


@pytest.mark.asyncio
async def test_system_spawn_creates_gate(session_factory):
    """With spawn probability forced to 1.0, a gate is always created."""
    original_prob = settings.system_spawn_probability
    settings.system_spawn_probability = 1.0
    try:
        async with session_factory() as session:
            treasury_id = await _get_treasury_id(session)
            rng = TickRNG(12345)
            gate = await system_spawn_gate(
                session, tick_number=1, tick_id=1, rng=rng, treasury_id=treasury_id
            )
            assert gate is not None
            assert gate.status == GateStatus.OFFERING
            assert gate.discovery_type.value == "SYSTEM"
            assert gate.discoverer_id is None
            assert gate.stability > 0

            # Shares assigned to treasury
            result = await session.execute(
                select(GateShare).where(
                    GateShare.gate_id == gate.id,
                    GateShare.player_id == treasury_id,
                )
            )
            share = result.scalar_one()
            assert share.quantity == gate.total_shares
            await session.commit()
    finally:
        settings.system_spawn_probability = original_prob


@pytest.mark.asyncio
async def test_system_spawn_skipped_on_low_roll(session_factory):
    """With spawn probability 0, no gate is created."""
    original_prob = settings.system_spawn_probability
    settings.system_spawn_probability = 0.0
    try:
        async with session_factory() as session:
            treasury_id = await _get_treasury_id(session)
            rng = TickRNG(12345)
            gate = await system_spawn_gate(
                session, tick_number=1, tick_id=1, rng=rng, treasury_id=treasury_id
            )
            assert gate is None
    finally:
        settings.system_spawn_probability = original_prob


@pytest.mark.asyncio
async def test_system_spawn_over_multiple_ticks(session_factory, pause_simulation):
    """Run 30 ticks with default probability — expect at least 1 gate."""
    for _ in range(30):
        await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(select(func.count(Gate.id)))
        count = result.scalar_one()
        assert count >= 1, f"Expected at least 1 gate after 30 ticks, got {count}"


# ── Player Discovery Tests ──


@pytest.mark.asyncio
async def test_player_discovery_creates_gate(session_factory, pause_simulation):
    """Player discovery deducts cost and creates a gate."""
    async with session_factory() as session:
        player = await _create_funded_player(session, balance=500_000)
        treasury = await _get_treasury(session)
        treasury_before = treasury.balance_micro
        await session.commit()

    async with session_factory() as session:
        intent = Intent(
            player_id=player.id,
            intent_type=IntentType.DISCOVER_GATE,
            payload={"min_rank": "E"},
            status=IntentStatus.QUEUED,
        )
        session.add(intent)
        await session.commit()

    await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(
            select(Intent).where(Intent.player_id == player.id)
        )
        processed = result.scalar_one()
        assert processed.status == IntentStatus.EXECUTED

        result = await session.execute(
            select(Gate).where(Gate.discoverer_id == player.id)
        )
        gate = result.scalar_one()
        assert gate.discovery_type.value == "PLAYER"
        assert gate.status == GateStatus.OFFERING

        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player.id)
        )
        player_balance = result.scalar_one()
        assert player_balance == 500_000 - 100_000

        treasury = await _get_treasury(session)
        assert treasury.balance_micro == treasury_before + 100_000


@pytest.mark.asyncio
async def test_discovery_insufficient_balance_rejected(
    session_factory, pause_simulation
):
    """Discovery with insufficient balance → REJECTED, no gate, no balance change."""
    async with session_factory() as session:
        player = await _create_funded_player(session, balance=50_000)
        await session.commit()

    async with session_factory() as session:
        intent = Intent(
            player_id=player.id,
            intent_type=IntentType.DISCOVER_GATE,
            payload={"min_rank": "E"},
            status=IntentStatus.QUEUED,
        )
        session.add(intent)
        await session.commit()

    await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(
            select(Intent).where(Intent.player_id == player.id)
        )
        processed = result.scalar_one()
        assert processed.status == IntentStatus.REJECTED
        assert "Insufficient balance" in processed.reject_reason

        result = await session.execute(
            select(func.count(Gate.id)).where(Gate.discoverer_id == player.id)
        )
        assert result.scalar_one() == 0

        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player.id)
        )
        assert result.scalar_one() == 50_000


# ── Gate Lifecycle Tests ──


@pytest.mark.asyncio
async def test_offering_transitions_to_active(session_factory):
    """Gate transitions from OFFERING to ACTIVE after offering period."""
    original_ticks = settings.gate_offering_ticks
    settings.gate_offering_ticks = 3
    try:
        async with session_factory() as session:
            treasury_id = await _get_treasury_id(session)

            gate = Gate(
                rank=GateRank.E,
                stability=100.0,
                volatility=0.05,
                base_yield_micro=2000,
                total_shares=100,
                status=GateStatus.OFFERING,
                spawned_at_tick=1,
                discovery_type=DiscoveryType.SYSTEM,
            )
            session.add(gate)
            await session.flush()
            session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=100))
            await session.commit()
            gate_id = gate.id

        async with session_factory() as session:
            rng = TickRNG(100)
            await advance_gate_lifecycle(session, tick_number=2, rng=rng)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(select(Gate).where(Gate.id == gate_id))
            assert result.scalar_one().status == GateStatus.OFFERING

        async with session_factory() as session:
            rng = TickRNG(101)
            await advance_gate_lifecycle(session, tick_number=4, rng=rng)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(select(Gate).where(Gate.id == gate_id))
            assert result.scalar_one().status == GateStatus.ACTIVE
    finally:
        settings.gate_offering_ticks = original_ticks


@pytest.mark.asyncio
async def test_stability_decays_over_ticks(session_factory):
    """Active gate stability decreases over time."""
    async with session_factory() as session:
        treasury_id = await _get_treasury_id(session)

        gate = Gate(
            rank=GateRank.E,
            stability=100.0,
            volatility=0.05,
            base_yield_micro=2000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=100))
        await session.commit()
        gate_id = gate.id

    for tick_num in range(2, 12):
        async with session_factory() as session:
            rng = TickRNG(tick_num * 1000)
            await advance_gate_lifecycle(session, tick_number=tick_num, rng=rng)
            await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(Gate).where(Gate.id == gate_id))
        gate = result.scalar_one()
        assert gate.stability < 100.0, "Stability should have decayed"


@pytest.mark.asyncio
async def test_gate_collapse_lifecycle(session_factory):
    """Gate with near-zero stability eventually collapses."""
    async with session_factory() as session:
        treasury_id = await _get_treasury_id(session)

        gate = Gate(
            rank=GateRank.E,
            stability=5.0,
            volatility=0.05,
            base_yield_micro=2000,
            total_shares=100,
            status=GateStatus.UNSTABLE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=100))
        await session.commit()
        gate_id = gate.id

    collapsed = False
    for tick_num in range(2, 50):
        async with session_factory() as session:
            rng = TickRNG(tick_num * 777)
            await advance_gate_lifecycle(session, tick_number=tick_num, rng=rng)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(select(Gate).where(Gate.id == gate_id))
            gate = result.scalar_one()
            if gate.status == GateStatus.COLLAPSED:
                collapsed = True
                assert gate.collapsed_at_tick is not None
                break

    assert collapsed, "Gate should have collapsed with stability=5 and threshold=20"


# ── Yield Distribution Tests ──


@pytest.mark.asyncio
async def test_yield_paid_to_shareholders(session_factory):
    """Active gate distributes yield from treasury to shareholders."""
    async with session_factory() as session:
        treasury_id = await _get_treasury_id(session)
        player = await _create_funded_player(session, balance=0)

        gate = Gate(
            rank=GateRank.E,
            stability=100.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()

        session.add(GateShare(gate_id=gate.id, player_id=player.id, quantity=50))
        session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=50))
        await session.commit()

        gate_id = gate.id
        player_id = player.id

    async with session_factory() as session:
        treasury_before = (await _get_treasury(session)).balance_micro
        await distribute_yield(
            session, tick_id=1, treasury_id=await _get_treasury_id(session)
        )
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player_id)
        )
        player_balance = result.scalar_one()
        assert player_balance == 5_000

        treasury = await _get_treasury(session)
        assert treasury.balance_micro == treasury_before - 5_000


@pytest.mark.asyncio
async def test_no_yield_for_collapsed_gate(session_factory):
    """Collapsed gates generate no yield."""
    async with session_factory() as session:
        treasury_id = await _get_treasury_id(session)
        player = await _create_funded_player(session, balance=0)

        gate = Gate(
            rank=GateRank.E,
            stability=50.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.COLLAPSED,
            spawned_at_tick=1,
            collapsed_at_tick=5,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(GateShare(gate_id=gate.id, player_id=player.id, quantity=50))
        await session.commit()
        player_id = player.id

    async with session_factory() as session:
        await distribute_yield(
            session, tick_id=1, treasury_id=await _get_treasury_id(session)
        )
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player_id)
        )
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_concentrated_holder_gets_reduced_yield(session_factory):
    """Ownership >50% receives reduced effective yield (80% band)."""
    async with session_factory() as session:
        treasury_id = await _get_treasury_id(session)
        player = await _create_funded_player(session, balance=0)

        gate = Gate(
            rank=GateRank.E,
            stability=100.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()

        session.add(GateShare(gate_id=gate.id, player_id=player.id, quantity=60))
        session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=40))
        await session.commit()
        player_id = player.id

    async with session_factory() as session:
        treasury_before = (await _get_treasury(session)).balance_micro
        await distribute_yield(
            session, tick_id=1, treasury_id=await _get_treasury_id(session)
        )
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player_id)
        )
        assert result.scalar_one() == 4_800
        treasury_after = (await _get_treasury(session)).balance_micro
        assert treasury_before - treasury_after == 4_800


@pytest.mark.asyncio
async def test_no_yield_when_treasury_empty(session_factory):
    """Yield distribution gracefully handles empty treasury."""
    async with session_factory() as session:
        treasury = await _get_treasury(session)
        treasury_id = treasury.id
        drain_amount = treasury.balance_micro

        drainer = await _create_funded_player(session, balance=drain_amount)

        gate = Gate(
            rank=GateRank.E,
            stability=100.0,
            volatility=0.05,
            base_yield_micro=10_000,
            total_shares=100,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.flush()
        session.add(GateShare(gate_id=gate.id, player_id=drainer.id, quantity=100))
        await session.commit()
        drainer_id = drainer.id

    async with session_factory() as session:
        treasury = await _get_treasury(session)
        assert treasury.balance_micro == 0

        # This should not raise — graceful degradation
        await distribute_yield(session, tick_id=1, treasury_id=treasury.id)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == drainer_id)
        )
        # Player got no yield — treasury was empty
        assert result.scalar_one() == drain_amount


# ── Conservation Invariant ──


@pytest.mark.asyncio
async def test_conservation_after_gates(session_factory, pause_simulation):
    """Conservation holds after spawns + discovery + yield distribution."""
    async with session_factory() as session:
        player = await _create_funded_player(session, balance=1_000_000)
        await session.commit()

    async with session_factory() as session:
        intent = Intent(
            player_id=player.id,
            intent_type=IntentType.DISCOVER_GATE,
            payload={"min_rank": "E"},
            status=IntentStatus.QUEUED,
        )
        session.add(intent)
        await session.commit()

    for _ in range(10):
        await execute_tick(session_factory)

    async with session_factory() as session:
        treasury = await _get_treasury(session)
        result = await session.execute(select(func.sum(Player.balance_micro)))
        total_player_balance = result.scalar_one() or 0

        total = treasury.balance_micro + total_player_balance
        assert total == settings.initial_seed_micro, (
            f"Conservation violated: treasury={treasury.balance_micro} + "
            f"players={total_player_balance} = {total}, "
            f"expected {settings.initial_seed_micro}"
        )
