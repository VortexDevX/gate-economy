"""Event engine — stochastic world events that shake the economy."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.event import Event, EventType
from app.models.gate import Gate, GateRankProfile, GateShare, GateStatus
from app.models.guild import Guild, GuildGateHolding, GuildStatus
from app.models.ledger import AccountEntityType, EntryType
from app.services.gate_lifecycle import spawn_gate
from app.services.transfer import InsufficientBalance, transfer
from app.simulation.rng import TickRNG

logger = structlog.get_logger()

EVENT_WEIGHTS: dict[EventType, int] = {
    EventType.STABILITY_SURGE: 25,
    EventType.STABILITY_CRISIS: 25,
    EventType.YIELD_BOOM: 20,
    EventType.MARKET_SHOCK: 15,
    EventType.DISCOVERY_SURGE: 15,
}


async def roll_events(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> list[Event]:
    """Roll for a stochastic event this tick. Returns 0 or 1 events."""
    if rng.random() >= settings.event_probability:
        return []

    types = list(EVENT_WEIGHTS.keys())
    weights = [float(EVENT_WEIGHTS[t]) for t in types]
    chosen = rng.choices(types, weights=weights, k=1)[0]

    handlers = {
        EventType.STABILITY_SURGE: _handle_stability_surge,
        EventType.STABILITY_CRISIS: _handle_stability_crisis,
        EventType.YIELD_BOOM: _handle_yield_boom,
        EventType.MARKET_SHOCK: _handle_market_shock,
        EventType.DISCOVERY_SURGE: _handle_discovery_surge,
    }

    event = await handlers[chosen](session, tick_number, tick_id, rng, treasury_id)
    if event is None:
        return []

    session.add(event)
    return [event]


# ── Handlers ──


async def _handle_stability_surge(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Event | None:
    result = await session.execute(
        select(Gate).where(
            Gate.status.in_([GateStatus.ACTIVE, GateStatus.UNSTABLE])
        )
    )
    gates = list(result.scalars().all())
    if not gates:
        return None

    gate = rng.choice(gates)
    change = rng.uniform(
        settings.event_stability_surge_min,
        settings.event_stability_surge_max,
    )

    # Cap at initial stability for this rank
    prof_result = await session.execute(
        select(GateRankProfile).where(GateRankProfile.rank == gate.rank)
    )
    profile = prof_result.scalar_one()

    gate.stability = min(gate.stability + change, profile.stability_init)

    logger.info(
        "event_stability_surge",
        gate_id=str(gate.id),
        change=round(change, 2),
        new_stability=round(gate.stability, 2),
    )

    return Event(
        event_type=EventType.STABILITY_SURGE,
        tick_id=tick_id,
        target_id=gate.id,
        payload={
            "change": round(change, 2),
            "new_stability": round(gate.stability, 2),
            "rank": gate.rank.value,
        },
    )


async def _handle_stability_crisis(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Event | None:
    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.ACTIVE)
    )
    gates = list(result.scalars().all())
    if not gates:
        return None

    gate = rng.choice(gates)
    change = rng.uniform(
        settings.event_stability_crisis_min,
        settings.event_stability_crisis_max,
    )

    gate.stability = max(gate.stability - change, 0.0)

    logger.info(
        "event_stability_crisis",
        gate_id=str(gate.id),
        change=round(change, 2),
        new_stability=round(gate.stability, 2),
    )

    return Event(
        event_type=EventType.STABILITY_CRISIS,
        tick_id=tick_id,
        target_id=gate.id,
        payload={
            "change": round(change, 2),
            "new_stability": round(gate.stability, 2),
            "rank": gate.rank.value,
        },
    )


async def _handle_yield_boom(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Event | None:
    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.ACTIVE)
    )
    gates = list(result.scalars().all())
    if not gates:
        return None

    gate = rng.choice(gates)
    multiplier = rng.uniform(
        settings.event_yield_boom_min_multiplier,
        settings.event_yield_boom_max_multiplier,
    )
    bonus_yield = int(
        gate.base_yield_micro * (gate.stability / 100.0) * multiplier
    )
    if bonus_yield <= 0:
        return None

    # ── Gather shareholders (same pattern as distribute_yield) ──
    share_result = await session.execute(
        select(GateShare).where(
            GateShare.gate_id == gate.id, GateShare.quantity > 0
        )
    )
    all_shares = list(share_result.scalars().all())

    guild_result = await session.execute(
        select(GuildGateHolding).where(
            GuildGateHolding.gate_id == gate.id,
            GuildGateHolding.quantity > 0,
        )
    )
    guild_holdings = list(guild_result.scalars().all())

    total_held = sum(s.quantity for s in all_shares) + sum(
        gh.quantity for gh in guild_holdings
    )
    if total_held == 0:
        return None

    player_shares = [s for s in all_shares if s.player_id != treasury_id]
    if not player_shares and not guild_holdings:
        return None  # only treasury holds shares

    # ── Pay player shareholders ──
    for share in sorted(player_shares, key=lambda s: str(s.player_id)):
        payout = bonus_yield * share.quantity // total_held
        if payout <= 0:
            continue
        try:
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=AccountEntityType.PLAYER,
                to_id=share.player_id,
                amount=payout,
                entry_type=EntryType.YIELD_PAYMENT,
                memo=f"Yield boom from gate {gate.id} ({multiplier:.1f}x)",
                tick_id=tick_id,
            )
        except InsufficientBalance:
            logger.warning("treasury_exhausted_yield_boom", gate_id=str(gate.id))
            break

    # ── Pay guild shareholders ──
    for gh in sorted(guild_holdings, key=lambda g: str(g.guild_id)):
        payout = bonus_yield * gh.quantity // total_held
        if payout <= 0:
            continue

        g_result = await session.execute(
            select(Guild.status).where(Guild.id == gh.guild_id)
        )
        guild_status = g_result.scalar_one_or_none()
        if guild_status == GuildStatus.INSOLVENT:
            payout = payout // 2
            if payout <= 0:
                continue

        try:
            await transfer(
                session=session,
                from_type=AccountEntityType.SYSTEM,
                from_id=treasury_id,
                to_type=AccountEntityType.GUILD,
                to_id=gh.guild_id,
                amount=payout,
                entry_type=EntryType.YIELD_PAYMENT,
                memo=f"Guild yield boom from gate {gate.id} ({multiplier:.1f}x)",
                tick_id=tick_id,
            )
        except InsufficientBalance:
            logger.warning("treasury_exhausted_guild_yield_boom")
            break

    logger.info(
        "event_yield_boom",
        gate_id=str(gate.id),
        multiplier=round(multiplier, 2),
        bonus_yield=bonus_yield,
    )

    return Event(
        event_type=EventType.YIELD_BOOM,
        tick_id=tick_id,
        target_id=gate.id,
        payload={
            "multiplier": round(multiplier, 2),
            "bonus_yield": bonus_yield,
            "rank": gate.rank.value,
        },
    )


async def _handle_market_shock(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Event | None:
    result = await session.execute(
        select(Gate).where(
            Gate.status.in_([GateStatus.ACTIVE, GateStatus.UNSTABLE])
        )
    )
    gates = list(result.scalars().all())
    if not gates:
        return None

    change = rng.uniform(
        settings.event_market_shock_min,
        settings.event_market_shock_max,
    )

    for gate in gates:
        gate.stability = max(gate.stability - change, 0.0)

    logger.info(
        "event_market_shock",
        change=round(change, 2),
        affected_count=len(gates),
    )

    return Event(
        event_type=EventType.MARKET_SHOCK,
        tick_id=tick_id,
        target_id=None,
        payload={"change": round(change, 2), "affected_count": len(gates)},
    )


async def _handle_discovery_surge(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Event | None:
    count = rng.randint(
        settings.event_discovery_surge_min,
        settings.event_discovery_surge_max,
    )
    spawned = 0
    for _ in range(count):
        gate = await spawn_gate(session, tick_number, tick_id, rng, treasury_id)
        if gate is not None:
            spawned += 1

    if spawned == 0:
        return None

    logger.info("event_discovery_surge", count=spawned)

    return Event(
        event_type=EventType.DISCOVERY_SURGE,
        tick_id=tick_id,
        target_id=None,
        payload={"count": spawned},
    )