import pytest
from sqlalchemy import delete, select

from app.models.intent import Intent, IntentStatus, IntentType
from app.models.tick import Tick
from app.simulation.state_hash import compute_state_hash
from app.simulation.tick import execute_tick


async def _clean_ticks_and_intents(session_factory):
    """Delete all intents then ticks (FK order)."""
    async with session_factory() as session:
        await session.execute(delete(Intent))
        await session.execute(delete(Tick))
        await session.commit()


@pytest.mark.asyncio
async def test_single_tick_creates_record(session_factory, pause_simulation):
    """Executing one tick creates a correctly populated tick record."""
    await _clean_ticks_and_intents(session_factory)

    tick = await execute_tick(session_factory)

    assert tick.tick_number == 1
    assert tick.seed is not None
    assert tick.started_at is not None
    assert tick.completed_at is not None
    assert tick.completed_at >= tick.started_at
    assert tick.intent_count == 0
    assert tick.state_hash is not None
    assert len(tick.state_hash) == 64


@pytest.mark.asyncio
async def test_sequential_tick_numbering(session_factory, pause_simulation):
    """Multiple ticks produce sequential tick_numbers with unique seeds."""
    await _clean_ticks_and_intents(session_factory)

    ticks = []
    for _ in range(3):
        tick = await execute_tick(session_factory)
        ticks.append(tick)

    assert [t.tick_number for t in ticks] == [1, 2, 3]

    seeds = {t.seed for t in ticks}
    assert len(seeds) == 3


@pytest.mark.asyncio
async def test_intents_collected_and_executed(
    session_factory, pause_simulation, test_player_id
):
    """Queued intents are collected by the tick and processed.

    CREATE_GUILD will be REJECTED (player has 0 balance).
    GUILD_INVEST will be REJECTED (guild doesn't exist).
    The test verifies the collection/routing machinery works —
    intents are picked up, processed, and marked with processed_tick.
    """
    await _clean_ticks_and_intents(session_factory)

    # Insert two queued intents (both will be rejected due to validation)
    async with session_factory() as session:
        intent_a = Intent(
            player_id=test_player_id,
            intent_type=IntentType.CREATE_GUILD,
            payload={"name": "TestGuild"},
            status=IntentStatus.QUEUED,
        )
        intent_b = Intent(
            player_id=test_player_id,
            intent_type=IntentType.GUILD_INVEST,
            payload={"guild_id": "00000000-0000-0000-0000-000000000000"},
            status=IntentStatus.QUEUED,
        )
        session.add_all([intent_a, intent_b])
        await session.commit()
        id_a, id_b = intent_a.id, intent_b.id

    # Run tick
    tick = await execute_tick(session_factory)

    assert tick.intent_count == 2

    # Verify both intents were collected and processed (REJECTED by validation)
    async with session_factory() as session:
        for intent_id in (id_a, id_b):
            result = await session.execute(
                select(Intent).where(Intent.id == intent_id)
            )
            intent = result.scalar_one()
            assert intent.status == IntentStatus.REJECTED
            assert intent.processed_tick == tick.id
            assert intent.reject_reason is not None


@pytest.mark.asyncio
async def test_state_hash_matches_recomputation(
    session_factory, pause_simulation
):
    """State hash stored in tick matches independent recomputation."""
    await _clean_ticks_and_intents(session_factory)

    tick = await execute_tick(session_factory)

    async with session_factory() as session:
        recomputed = await compute_state_hash(session)

    assert recomputed == tick.state_hash