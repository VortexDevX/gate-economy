"""Leaderboard and season management.

Computes net worth (balance + portfolio value) for all players,
applies activity-based score decay, and manages seasonal competitions.

No new currency flows — purely derived/read state.
"""

import uuid
from collections import defaultdict

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gate import Gate, GateShare, GateStatus
from app.models.guild import Guild, GuildShare, GuildStatus
from app.models.intent import Intent, IntentStatus
from app.models.leaderboard import (
    PlayerNetWorth,
    Season,
    SeasonResult,
    SeasonStatus,
)
from app.models.market import AssetType, MarketPrice, Order
from app.models.player import Player
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.services.anti_exploit import _share_value_micro

logger = structlog.get_logger()


def _apply_decay(
    net_worth_micro: int, tick_number: int, last_active_tick: int
) -> int:
    """Compute score with activity-based decay.

    Grace period: no decay for leaderboard_decay_inactive_ticks after last activity.
    After grace: linear decay at leaderboard_decay_rate per tick.
    Floor: score never drops below decay_floor × net_worth.
    """
    inactive = max(
        0,
        tick_number
        - last_active_tick
        - settings.leaderboard_decay_inactive_ticks,
    )
    if inactive <= 0:
        return net_worth_micro
    multiplier = max(
        settings.leaderboard_decay_floor,
        1.0 - settings.leaderboard_decay_rate * inactive,
    )
    return int(net_worth_micro * multiplier)


async def _batch_last_active_ticks(
    session: AsyncSession,
) -> dict[uuid.UUID, int]:
    """Derive last activity tick for all players from intents and orders."""
    # Intents: join with ticks to get tick_number (processed_tick is FK to ticks.id)
    result = await session.execute(
        select(
            Intent.player_id,
            func.max(Tick.tick_number),
        )
        .join(Tick, Intent.processed_tick == Tick.id)
        .where(Intent.status == IntentStatus.EXECUTED)
        .group_by(Intent.player_id)
    )
    intent_activity: dict[uuid.UUID, int] = {
        row[0]: row[1] for row in result.all()
    }

    # Orders: created_at_tick is already tick_number
    result = await session.execute(
        select(
            Order.player_id,
            func.max(Order.created_at_tick),
        )
        .where(Order.is_system == False)  # noqa: E712
        .group_by(Order.player_id)
    )
    order_activity: dict[uuid.UUID, int] = {
        row[0]: row[1] for row in result.all()
    }

    # Merge: take max per player
    all_player_ids = set(intent_activity) | set(order_activity)
    merged: dict[uuid.UUID, int] = {}
    for pid in all_player_ids:
        merged[pid] = max(
            intent_activity.get(pid, 0),
            order_activity.get(pid, 0),
        )
    return merged


async def update_leaderboard(
    session: AsyncSession, tick_number: int, tick_id: int
) -> None:
    """Batch-update net worth and score for all players.

    Includes AI players for data completeness — API layer filters them out.
    """
    # Load treasury ID
    result = await session.execute(
        select(SystemAccount.id).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury_id = result.scalar_one()

    # Load all players
    result = await session.execute(select(Player))
    players = list(result.scalars().all())
    if not players:
        return

    # ── Gate share portfolio ──
    result = await session.execute(
        select(GateShare, Gate)
        .join(Gate, GateShare.gate_id == Gate.id)
        .where(
            GateShare.player_id != treasury_id,
            GateShare.quantity > 0,
            Gate.status.in_([GateStatus.ACTIVE, GateStatus.UNSTABLE]),
        )
    )
    gate_holdings = result.all()

    gate_ids = list({gs.gate_id for gs, _ in gate_holdings})
    gate_mps: dict[uuid.UUID, MarketPrice] = {}
    if gate_ids:
        mp_result = await session.execute(
            select(MarketPrice).where(
                MarketPrice.asset_type == AssetType.GATE_SHARE,
                MarketPrice.asset_id.in_(gate_ids),
            )
        )
        gate_mps = {mp.asset_id: mp for mp in mp_result.scalars().all()}

    gate_portfolio: dict[uuid.UUID, int] = defaultdict(int)
    for gs, gate in gate_holdings:
        mp = gate_mps.get(gate.id)
        per_share = _share_value_micro(gate, mp)
        gate_portfolio[gs.player_id] += per_share * gs.quantity

    # ── Guild share portfolio ──
    result = await session.execute(select(Guild.id))
    all_guild_ids = {row[0] for row in result.all()}

    result = await session.execute(
        select(GuildShare, Guild)
        .join(Guild, GuildShare.guild_id == Guild.id)
        .where(
            GuildShare.quantity > 0,
            Guild.status.in_([GuildStatus.ACTIVE, GuildStatus.INSOLVENT]),
        )
    )
    guild_holdings = result.all()

    guild_ids_held = list({gsh.guild_id for gsh, _ in guild_holdings})
    guild_mps: dict[uuid.UUID, MarketPrice] = {}
    if guild_ids_held:
        mp_result = await session.execute(
            select(MarketPrice).where(
                MarketPrice.asset_type == AssetType.GUILD_SHARE,
                MarketPrice.asset_id.in_(guild_ids_held),
            )
        )
        guild_mps = {mp.asset_id: mp for mp in mp_result.scalars().all()}

    guild_fallback_price = (
        settings.guild_creation_cost_micro // settings.guild_total_shares
    )
    guild_portfolio: dict[uuid.UUID, int] = defaultdict(int)
    for gsh, guild in guild_holdings:
        # Skip guild self-held float and treasury-held shares
        if gsh.player_id in all_guild_ids or gsh.player_id == treasury_id:
            continue
        mp = guild_mps.get(guild.id)
        if mp and mp.last_price_micro:
            per_share = mp.last_price_micro
        else:
            per_share = guild_fallback_price
        guild_portfolio[gsh.player_id] += per_share * gsh.quantity

    # ── Activity data ──
    activity_map = await _batch_last_active_ticks(session)

    # ── Load existing net worth rows for upsert ──
    result = await session.execute(select(PlayerNetWorth))
    existing = {pnw.player_id: pnw for pnw in result.scalars().all()}

    # ── Compute and upsert ──
    for player in players:
        portfolio = gate_portfolio.get(player.id, 0) + guild_portfolio.get(
            player.id, 0
        )
        net_worth = player.balance_micro + portfolio
        last_active = activity_map.get(player.id, 0)
        score = _apply_decay(net_worth, tick_number, last_active)

        pnw = existing.get(player.id)
        if pnw is None:
            pnw = PlayerNetWorth(player_id=player.id)
            session.add(pnw)

        pnw.net_worth_micro = net_worth
        pnw.score_micro = score
        pnw.balance_micro = player.balance_micro
        pnw.portfolio_micro = portfolio
        pnw.last_active_tick = last_active
        pnw.updated_at_tick = tick_number

    logger.info(
        "leaderboard_updated",
        tick_number=tick_number,
        player_count=len(players),
    )


async def check_season(
    session: AsyncSession, tick_number: int, tick_id: int
) -> None:
    """Season lifecycle: create first season or rotate when duration exceeded.

    Uses savepoints to handle concurrent tick execution gracefully
    (e.g., worker + test both calling execute_tick simultaneously).
    """
    from sqlalchemy.exc import IntegrityError

    result = await session.execute(
        select(Season).where(Season.status == SeasonStatus.ACTIVE)
    )
    active_season = result.scalar_one_or_none()

    if active_season is None:
        try:
            async with session.begin_nested():
                season = Season(
                    season_number=1,
                    start_tick=tick_number,
                    status=SeasonStatus.ACTIVE,
                )
                session.add(season)
        except IntegrityError:
            # Another concurrent transaction created it — safe to continue
            pass
        logger.info("season_created", season_number=1, start_tick=tick_number)
        return

    if tick_number - active_season.start_tick >= settings.season_duration_ticks:
        await finalize_season(session, active_season, tick_number, tick_id)
        next_number = active_season.season_number + 1
        try:
            async with session.begin_nested():
                new_season = Season(
                    season_number=next_number,
                    start_tick=tick_number,
                    status=SeasonStatus.ACTIVE,
                )
                session.add(new_season)
        except IntegrityError:
            pass
        logger.info(
            "season_rotated",
            old_season=active_season.season_number,
            new_season=next_number,
        )


async def finalize_season(
    session: AsyncSession,
    season: Season,
    tick_number: int,
    tick_id: int,
) -> None:
    """Record final standings and complete the season."""
    # Force fresh leaderboard update
    await update_leaderboard(session, tick_number, tick_id)

    # Load non-AI player scores ordered by score DESC
    result = await session.execute(
        select(PlayerNetWorth)
        .join(Player, PlayerNetWorth.player_id == Player.id)
        .where(Player.is_ai == False)  # noqa: E712
        .order_by(PlayerNetWorth.score_micro.desc())
    )
    entries = list(result.scalars().all())

    for rank, entry in enumerate(entries, 1):
        session.add(
            SeasonResult(
                season_id=season.id,
                player_id=entry.player_id,
                final_rank=rank,
                final_score_micro=entry.score_micro,
                final_net_worth_micro=entry.net_worth_micro,
            )
        )

    season.status = SeasonStatus.COMPLETED
    season.end_tick = tick_number

    logger.info(
        "season_finalized",
        season_number=season.season_number,
        result_count=len(entries),
    )