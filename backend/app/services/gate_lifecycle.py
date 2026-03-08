"""Gate lifecycle service — spawn, discover, decay, yield distribution."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import (
    DiscoveryType,
    Gate,
    GateRank,
    GateRankProfile,
    GateShare,
    GateStatus,
)
from app.models.guild import Guild, GuildGateHolding, GuildStatus
from app.models.intent import Intent, IntentStatus
from app.models.ledger import AccountEntityType, EntryType
from app.services.transfer import InsufficientBalance, transfer
from app.simulation.rng import TickRNG

logger = structlog.get_logger()

# Rank order for upgrade rolls (lowest → highest)
RANK_ORDER: list[GateRank] = list(GateRank)
RANK_UPGRADE_CHANCE: float = 0.15


def _yield_concentration_multiplier(ownership_pct: float) -> float:
    """Yield effectiveness by concentration band (Phase 9 canonical model)."""
    if ownership_pct > 0.90:
        return 0.30
    if ownership_pct > 0.75:
        return 0.60
    if ownership_pct > 0.50:
        return 0.80
    return 1.0


# ── Internal helpers ──


async def _load_profiles(
    session: AsyncSession,
) -> dict[GateRank, GateRankProfile]:
    """Load all gate rank profiles into a dict keyed by rank."""
    result = await session.execute(select(GateRankProfile))
    return {p.rank: p for p in result.scalars().all()}


async def _create_gate(
    session: AsyncSession,
    profile: GateRankProfile,
    tick_number: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
    discovery_type: DiscoveryType,
    discoverer_id: uuid.UUID | None = None,
) -> Gate:
    """Create a gate with randomized params and assign all shares to treasury."""
    gate = Gate(
        rank=profile.rank,
        stability=profile.stability_init,
        volatility=profile.volatility * rng.uniform(0.8, 1.2),
        base_yield_micro=rng.randint(
            profile.yield_min_micro, profile.yield_max_micro
        ),
        total_shares=profile.total_shares,
        status=GateStatus.OFFERING,
        spawned_at_tick=tick_number,
        discovery_type=discovery_type,
        discoverer_id=discoverer_id,
    )
    session.add(gate)
    await session.flush()  # populate gate.id

    # Treasury holds all initial shares (sold via market in Phase 5)
    share = GateShare(
        gate_id=gate.id,
        player_id=treasury_id,
        quantity=profile.total_shares,
    )
    session.add(share)

    logger.info(
        "gate_created",
        gate_id=str(gate.id),
        rank=gate.rank.value,
        stability=round(gate.stability, 2),
        base_yield_micro=gate.base_yield_micro,
        total_shares=gate.total_shares,
        discovery_type=discovery_type.value,
    )
    return gate


def _roll_rank_upgrade(rng: TickRNG, min_rank: GateRank) -> GateRank:
    """Starting at min_rank, roll for tier upgrades (15% chance each)."""
    idx = RANK_ORDER.index(min_rank)
    while idx < len(RANK_ORDER) - 1:
        if rng.random() < RANK_UPGRADE_CHANCE:
            idx += 1
        else:
            break
    return RANK_ORDER[idx]


# ── Public API (called from tick pipeline) ──

async def spawn_gate(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Gate | None:
    """Unconditionally spawn one system gate. Used by system_spawn and events."""
    profiles = await _load_profiles(session)
    if not profiles:
        logger.warning("no_rank_profiles_found")
        return None

    ranks = list(profiles.keys())
    weights = [float(profiles[r].spawn_weight) for r in ranks]
    selected_rank = rng.choices(ranks, weights=weights, k=1)[0]
    profile = profiles[selected_rank]

    return await _create_gate(
        session=session,
        profile=profile,
        tick_number=tick_number,
        rng=rng,
        treasury_id=treasury_id,
        discovery_type=DiscoveryType.SYSTEM,
    )

async def system_spawn_gate(
    session: AsyncSession,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> Gate | None:
    """Roll for a system-spawned gate. Returns Gate if spawned, else None."""
    if rng.random() >= settings.system_spawn_probability:
        return None
    return await spawn_gate(session, tick_number, tick_id, rng, treasury_id)


async def process_discover_intent(
    session: AsyncSession,
    intent: Intent,
    tick_number: int,
    tick_id: int,
    rng: TickRNG,
    treasury_id: uuid.UUID,
) -> None:
    """Process a DISCOVER_GATE intent. Marks intent REJECTED on failure."""
    payload = intent.payload or {}
    min_rank_str = payload.get("min_rank", "E")

    # Validate rank
    try:
        min_rank = GateRank(min_rank_str)
    except ValueError:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"Invalid rank: {min_rank_str}"
        return

    # Load profiles
    profiles = await _load_profiles(session)
    if min_rank not in profiles:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = f"No profile for rank: {min_rank_str}"
        return

    profile = profiles[min_rank]

    # Transfer discovery cost: player → treasury (sink)
    try:
        await transfer(
            session=session,
            from_type=AccountEntityType.PLAYER,
            from_id=intent.player_id,
            to_type=AccountEntityType.SYSTEM,
            to_id=treasury_id,
            amount=profile.discovery_cost_micro,
            entry_type=EntryType.GATE_DISCOVERY,
            memo=f"Gate discovery (min rank: {min_rank.value})",
            tick_id=tick_id,
        )
    except InsufficientBalance:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = (
            f"Insufficient balance for {min_rank.value} discovery "
            f"(cost: {profile.discovery_cost_micro})"
        )
        return

    # Roll for rank upgrade (may get higher than min_rank)
    final_rank = _roll_rank_upgrade(rng, min_rank)
    final_profile = profiles[final_rank]

    gate = await _create_gate(
        session=session,
        profile=final_profile,
        tick_number=tick_number,
        rng=rng,
        treasury_id=treasury_id,
        discovery_type=DiscoveryType.PLAYER,
        discoverer_id=intent.player_id,
    )

    logger.info(
        "gate_discovered_by_player",
        player_id=str(intent.player_id),
        min_rank=min_rank.value,
        final_rank=final_rank.value,
        gate_id=str(gate.id),
        cost=profile.discovery_cost_micro,
    )


async def advance_gate_lifecycle(
    session: AsyncSession,
    tick_number: int,
    rng: TickRNG,
) -> None:
    """Advance all non-collapsed gates: OFFERING→ACTIVE, decay, collapse."""
    profiles = await _load_profiles(session)

    result = await session.execute(
        select(Gate)
        .where(
            Gate.status.in_([
                GateStatus.OFFERING,
                GateStatus.ACTIVE,
                GateStatus.UNSTABLE,
            ])
        )
        .with_for_update()
    )
    gates = list(result.scalars().all())

    for gate in gates:
        profile = profiles.get(gate.rank)
        if profile is None:
            continue

        # ── OFFERING → ACTIVE after offering period ──
        if gate.status == GateStatus.OFFERING:
            age = tick_number - gate.spawned_at_tick
            if age >= settings.gate_offering_ticks:
                gate.status = GateStatus.ACTIVE
                logger.info(
                    "gate_activated",
                    gate_id=str(gate.id),
                    rank=gate.rank.value,
                )
            continue  # OFFERING gates don't decay

        # ── ACTIVE / UNSTABLE: stability decay ──
        decay_rate = settings.gate_base_decay_rate * (
            1.0 + gate.volatility * rng.gauss(0, 0.3)
        )
        decay_rate = max(decay_rate, 0.0)  # no negative decay (no free stability)
        gate.stability -= decay_rate
        gate.stability = max(gate.stability, 0.0)  # floor at zero

        # ── ACTIVE → UNSTABLE when below threshold ──
        if (
            gate.status == GateStatus.ACTIVE
            and gate.stability < profile.collapse_threshold
        ):
            gate.status = GateStatus.UNSTABLE
            logger.info(
                "gate_unstable",
                gate_id=str(gate.id),
                stability=round(gate.stability, 2),
                threshold=profile.collapse_threshold,
            )

        # ── UNSTABLE → COLLAPSED (probabilistic) ──
        if gate.status == GateStatus.UNSTABLE:
            collapse_prob = (
                (profile.collapse_threshold - gate.stability)
                / profile.collapse_threshold
            )
            collapse_prob = max(collapse_prob, 0.0)
            if rng.random() < collapse_prob:
                gate.status = GateStatus.COLLAPSED
                gate.collapsed_at_tick = tick_number
                logger.info(
                    "gate_collapsed",
                    gate_id=str(gate.id),
                    rank=gate.rank.value,
                    stability=round(gate.stability, 2),
                )


async def distribute_yield(
    session: AsyncSession,
    tick_id: int,
    treasury_id: uuid.UUID,
) -> None:
    """Pay yield from treasury to shareholders of ACTIVE gates.

    - Only ACTIVE gates yield (not OFFERING, UNSTABLE, or COLLAPSED).
    - Concentration is handled yield-side:
      >50% => 80%, >75% => 60%, >90% => 30%.
    - Treasury-held shares are skipped (no self-payment).
    - Guild gate holdings receive yield to guild treasury.
    - Insolvent guilds receive 50% yield penalty.
    - Integer division for pro-rata; remainder stays in treasury.
    - If treasury is exhausted, distribution stops entirely.
    """
    result = await session.execute(
        select(Gate).where(Gate.status == GateStatus.ACTIVE)
    )
    active_gates = list(result.scalars().all())

    for gate in active_gates:
        effective_yield = int(gate.base_yield_micro * (gate.stability / 100.0))
        if effective_yield <= 0:
            continue

        # Player/treasury shareholders
        share_result = await session.execute(
            select(GateShare).where(
                GateShare.gate_id == gate.id,
                GateShare.quantity > 0,
            )
        )
        all_shares = list(share_result.scalars().all())

        # Guild shareholders
        guild_result = await session.execute(
            select(GuildGateHolding).where(
                GuildGateHolding.gate_id == gate.id,
                GuildGateHolding.quantity > 0,
            )
        )
        guild_holdings = list(guild_result.scalars().all())

        total_held = (
            sum(s.quantity for s in all_shares)
            + sum(gh.quantity for gh in guild_holdings)
        )
        if total_held == 0:
            continue

        # Player shares (skip treasury — no self-payment)
        player_shares = [s for s in all_shares if s.player_id != treasury_id]

        if not player_shares and not guild_holdings:
            continue  # only treasury holds shares

        # Pay player shareholders (concentration reduction applied here)
        player_shares.sort(key=lambda s: str(s.player_id))
        for share in player_shares:
            base_payout = effective_yield * share.quantity // total_held
            ownership_pct = share.quantity / gate.total_shares
            payout = int(
                base_payout * _yield_concentration_multiplier(ownership_pct)
            )
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
                    memo=f"Yield from gate {gate.id}",
                    tick_id=tick_id,
                )
            except InsufficientBalance:
                logger.warning(
                    "treasury_exhausted_during_yield",
                    gate_id=str(gate.id),
                    player_id=str(share.player_id),
                )
                return

        # Pay guild shareholders (guild-side concentration is not reduced here)
        guild_holdings.sort(key=lambda gh: str(gh.guild_id))
        for gh in guild_holdings:
            payout = effective_yield * gh.quantity // total_held
            if payout <= 0:
                continue

            # Insolvent guilds receive 50% yield
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
                    memo=f"Guild yield from gate {gate.id}",
                    tick_id=tick_id,
                )
            except InsufficientBalance:
                logger.warning(
                    "treasury_exhausted_during_guild_yield",
                    gate_id=str(gate.id),
                    guild_id=str(gh.guild_id),
                )
                return
