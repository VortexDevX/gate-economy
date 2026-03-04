import pytest
from sqlalchemy import delete

from app.models.gate import Gate, GateShare
from app.models.intent import Intent
from app.models.tick import Tick
from app.simulation.tick import execute_tick


async def _clean_simulation_state(session_factory):
    """Delete all simulation-created state (FK order preserved)."""
    async with session_factory() as session:
        await session.execute(delete(Intent))
        await session.execute(delete(GateShare))
        await session.execute(delete(Gate))
        await session.execute(delete(Tick))
        await session.commit()


async def _run_n_ticks(session_factory, n: int) -> list[dict]:
    """Execute n ticks and return list of {tick_number, seed, state_hash}."""
    results = []
    for _ in range(n):
        tick = await execute_tick(session_factory)
        results.append({
            "tick_number": tick.tick_number,
            "seed": tick.seed,
            "state_hash": tick.state_hash,
        })
    return results


@pytest.mark.asyncio
async def test_replay_produces_identical_results(
    session_factory, pause_simulation
):
    """Two runs of 5 ticks from the same initial state produce
    identical tick numbers, seeds, and state hashes."""

    # ── Run 1 ──
    await _clean_simulation_state(session_factory)
    run_1 = await _run_n_ticks(session_factory, 5)

    # ── Reset (including gates created by system spawn) ──
    await _clean_simulation_state(session_factory)

    # ── Run 2 ──
    run_2 = await _run_n_ticks(session_factory, 5)

    # ── Assert identical ──
    assert len(run_1) == len(run_2) == 5

    for r1, r2 in zip(run_1, run_2):
        assert r1["tick_number"] == r2["tick_number"]
        assert r1["seed"] == r2["seed"]
        assert r1["state_hash"] == r2["state_hash"]


@pytest.mark.asyncio
async def test_different_seed_produces_different_results(
    session_factory, pause_simulation
):
    """Changing the initial seed produces different tick seeds
    (verifies RNG chain is actually seed-dependent)."""
    from unittest.mock import patch

    await _clean_simulation_state(session_factory)
    run_1 = await _run_n_ticks(session_factory, 3)

    await _clean_simulation_state(session_factory)

    # Patch the initial seed to a different value
    with patch("app.simulation.tick.settings") as mock_settings:
        mock_settings.simulation_initial_seed = 9999
        run_2 = await _run_n_ticks(session_factory, 3)

    # Tick numbers match but seeds differ
    for r1, r2 in zip(run_1, run_2):
        assert r1["tick_number"] == r2["tick_number"]
        assert r1["seed"] != r2["seed"]