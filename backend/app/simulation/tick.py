from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.services.ai_traders import run_ai_traders
from app.services.event_engine import roll_events
from app.services.gate_lifecycle import (
    advance_gate_lifecycle,
    distribute_yield,
    process_discover_intent,
    system_spawn_gate,
)
from app.services.guild_manager import (
    auto_dividends,
    guild_maintenance,
    process_create_guild,
    process_guild_dividend,
    process_guild_invest,
)
from app.services.news_generator import generate_tick_news
from app.services.leaderboard import check_season, update_leaderboard
from app.services.order_matching import (
    cancel_collapsed_gate_orders,
    create_iso_orders,
    finalize_iso_transitions,
    match_orders,
    process_cancel_order,
    process_place_order,
    update_market_prices,
)
from app.services.realtime import publish_tick_update
from app.services.anti_exploit import run_anti_exploit_maintenance
from app.simulation.rng import TickRNG, derive_seed
from app.simulation.state_hash import compute_state_hash

logger = structlog.get_logger()

# ── Intent processing ──


async def _process_intents(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    intents: list[Intent],
    treasury_id: "uuid.UUID",  # type: ignore
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
        elif intent.intent_type == IntentType.PLACE_ORDER:
            await process_place_order(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                treasury_id=treasury_id,
            )
        elif intent.intent_type == IntentType.CANCEL_ORDER:
            await process_cancel_order(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                treasury_id=treasury_id,
            )
        elif intent.intent_type == IntentType.CREATE_GUILD:
            await process_create_guild(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                treasury_id=treasury_id,
            )
        elif intent.intent_type == IntentType.GUILD_DIVIDEND:
            await process_guild_dividend(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                treasury_id=treasury_id,
            )
        elif intent.intent_type == IntentType.GUILD_INVEST:
            await process_guild_invest(
                session=session,
                intent=intent,
                tick_number=tick_number,
                tick_id=tick_id,
                treasury_id=treasury_id,
            )


# ── Gate advancement ──


async def _advance_gates(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: "uuid.UUID",  # type: ignore
) -> None:
    """System spawn + lifecycle + yield distribution."""
    await system_spawn_gate(session, tick_number, tick_id, rng, treasury_id)
    await advance_gate_lifecycle(session, tick_number, rng)
    await distribute_yield(session, tick_id, treasury_id)


# ── Guild lifecycle ──


async def _guild_lifecycle(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    treasury_id: "uuid.UUID",  # type: ignore
) -> None:
    """Per-tick guild maintenance, insolvency, and auto-dividends."""
    await guild_maintenance(session, tick_number, tick_id, treasury_id)
    await auto_dividends(session, tick_number, tick_id)


# ── Main pipeline ──


async def execute_tick(session_factory: async_sessionmaker) -> Tick:
    """Execute one simulation tick.

    Must be called with the simulation lock held.
    All state mutations happen in a single DB transaction.

    Steps match the canonical pipeline from PLAN.md.
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

        # Load treasury ID (needed for gate + market + guild operations)
        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id: _uuid.UUID = result.scalar_one()

        # 4b. Load runtime parameters from DB (admin changes reflected within 1 tick)
        from app.services.admin import load_parameters_into_settings
        await load_parameters_into_settings(session)

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

        # 7b. Guild lifecycle (maintenance, insolvency, auto-dividends)
        await _guild_lifecycle(
            session, tick_number, tick.id, treasury_id
        )

        # 7c. AI traders (cancel old orders, run strategies)
        await run_ai_traders(session, tick_number, tick.id, treasury_id, rng)

        # 8. Create ISO orders for OFFERING gates + guild shares
        await create_iso_orders(session, tick_number, treasury_id)

        # 9. Cancel orders for COLLAPSED gates + DISSOLVED guilds
        await cancel_collapsed_gate_orders(
            session, tick_number, tick.id, treasury_id
        )

        # 10. Match orders
        await match_orders(session, tick_number, tick.id, treasury_id)

        # 11. Finalize ISO transitions (all shares sold → ACTIVE)
        await finalize_iso_transitions(session, tick_number, treasury_id)

        # 12. Update market prices
        await update_market_prices(session, tick_number, tick.id)

        # 13. Roll events
        events = await roll_events(
            session, tick_number, tick.id, rng, treasury_id
        )

        # 13b. Generate news
        news_items = await generate_tick_news(
            session, tick_number, tick.id, events
        )

        # 14. Anti-exploit maintenance (Phase 9+)
        await run_anti_exploit_maintenance(session, tick_number, tick.id, treasury_id)
    
        # 14b. Leaderboard & season updates
        await check_season(session, tick_number, tick.id)
        if tick_number % settings.net_worth_update_interval == 0:
            await update_leaderboard(session, tick_number, tick.id)

        # 15. Mark remaining PROCESSING intents as EXECUTED
        #     (REJECTED intents keep their status from step 6)
        for intent in intents:
            if intent.status == IntentStatus.PROCESSING:
                intent.status = IntentStatus.EXECUTED

        # 16. Compute state hash for replay verification
        state_hash = await compute_state_hash(session)

        # 17. Finalize tick record
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

        # 18. Publish realtime update (fire-and-forget, after commit)
        await publish_tick_update(tick_number, news_items)

        return tick