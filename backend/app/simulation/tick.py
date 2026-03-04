from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.services.gate_lifecycle import (
    advance_gate_lifecycle,
    distribute_yield,
    process_discover_intent,
    system_spawn_gate,
)
from app.simulation.rng import TickRNG, derive_seed
from app.simulation.state_hash import compute_state_hash

logger = structlog.get_logger()


# ── No-op hooks — filled in by future phases ──


async def _match_orders(
    session: AsyncSession, tick_number: int, rng: TickRNG
) -> None:
    """Phase 5+: Match market orders."""


async def _roll_events(
    session: AsyncSession, tick_number: int, rng: TickRNG
) -> None:
    """Phase 8+: Roll stochastic events."""


async def _anti_exploit_maintenance(
    session: AsyncSession, tick_number: int, rng: TickRNG
) -> None:
    """Phase 9+: Anti-exploit maintenance costs."""


# ── Intent processing ──


async def _process_intents(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    intents: list[Intent],
    treasury_id: "uuid.UUID", # type: ignore
) -> None:
    """Route intents to their respective processors."""
    for intent in intents:
        if intent.intent_type == IntentType.DISCOVER_GATE:
            await process_discover_intent(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                rng=rng,
                treasury_id=treasury_id,
            )
        # Phase 5+: PLACE_ORDER, CANCEL_ORDER
        # Phase 6+: CREATE_GUILD, GUILD_DIVIDEND, GUILD_INVEST


# ── Gate advancement ──


async def _advance_gates(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: "uuid.UUID", # type: ignore
) -> None:
    """System spawn + lifecycle + yield distribution."""
    await system_spawn_gate(session, tick_number, tick_id, rng, treasury_id)
    await advance_gate_lifecycle(session, tick_number, rng)
    await distribute_yield(session, tick_id, treasury_id)


# ── Main pipeline ──


async def execute_tick(session_factory: async_sessionmaker) -> Tick:
    """Execute one simulation tick.

    Must be called with the simulation lock held.
    All state mutations happen in a single DB transaction.

    Steps match the canonical pipeline from PLAN.md Phase 3.
    """
    import uuid as _uuid  # deferred to avoid circular at module level

    async with session_factory() as session:
        # 1. Determine tick_number from last completed tick
        result = await session.execute(
            select(Tick).order_by(Tick.tick_number.desc()).limit(1)
        )
        last_tick = result.scalar_one_or_none()

        if last_tick is None:
            tick_number = 1
            previous_seed = settings.simulation_initial_seed
        else:
            tick_number = last_tick.tick_number + 1
            previous_seed = last_tick.seed

        # 2. Derive deterministic seed
        seed = derive_seed(previous_seed, tick_number)

        # 3. Create tick-scoped RNG
        rng = TickRNG(seed)

        # 4. Insert tick record (marks start)
        tick = Tick(
            tick_number=tick_number,
            seed=seed,
            started_at=datetime.now(UTC),
        )
        session.add(tick)
        await session.flush()  # populate tick.id for FK references

        # Load treasury ID (needed for gate operations)
        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id: _uuid.UUID = result.scalar_one()

        # 5. Collect QUEUED intents → mark PROCESSING
        result = await session.execute(
            select(Intent)
            .where(Intent.status == IntentStatus.QUEUED)
            .order_by(Intent.created_at)
            .with_for_update()
        )
        intents = list(result.scalars().all())

        for intent in intents:
            intent.status = IntentStatus.PROCESSING
            intent.processed_tick = tick.id

        # 6. Process intents by type
        await _process_intents(
            session, tick_number, tick.id, rng, intents, treasury_id
        )

        # 7. Advance gates (spawn, decay, yield)
        await _advance_gates(
            session, tick_number, tick.id, rng, treasury_id
        )

        # 8. Match orders (Phase 5+)
        await _match_orders(session, tick_number, rng)

        # 9. Roll events (Phase 8+)
        await _roll_events(session, tick_number, rng)

        # 10. Anti-exploit maintenance (Phase 9+)
        await _anti_exploit_maintenance(session, tick_number, rng)

        # 11. Mark remaining PROCESSING intents as EXECUTED
        #     (REJECTED intents keep their status from step 6)
        for intent in intents:
            if intent.status == IntentStatus.PROCESSING:
                intent.status = IntentStatus.EXECUTED

        # 12. Compute state hash for replay verification
        state_hash = await compute_state_hash(session)

        # 13. Finalize tick record
        tick.completed_at = datetime.now(UTC)
        tick.intent_count = len(intents)
        tick.state_hash = state_hash

        # Atomic commit — all mutations or nothing
        await session.commit()

        logger.info(
            "tick_completed",
            tick_number=tick_number,
            seed=seed,
            intent_count=len(intents),
            state_hash=state_hash[:16],
        )

        return tick