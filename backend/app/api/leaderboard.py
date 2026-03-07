from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_player, get_db
from app.models.leaderboard import (
    PlayerNetWorth,
    Season,
    SeasonResult,
    SeasonStatus,
)
from app.models.player import Player
from app.schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardResponse,
    MyRankResponse,
    SeasonResponse,
)

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.leaderboard_size),
    db: AsyncSession = Depends(get_db),
):
    """Paginated leaderboard rankings (excludes AI players)."""
    # Total count
    count_result = await db.execute(
        select(func.count(PlayerNetWorth.player_id))
        .join(Player, PlayerNetWorth.player_id == Player.id)
        .where(Player.is_ai == False)  # noqa: E712
    )
    total = count_result.scalar_one()

    # Paginated entries
    offset = (page - 1) * page_size
    result = await db.execute(
        select(PlayerNetWorth, Player.username)
        .join(Player, PlayerNetWorth.player_id == Player.id)
        .where(Player.is_ai == False)  # noqa: E712
        .order_by(PlayerNetWorth.score_micro.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    entries = [
        LeaderboardEntry(
            rank=offset + idx + 1,
            player_id=pnw.player_id,
            username=username,
            score_micro=pnw.score_micro,
            net_worth_micro=pnw.net_worth_micro,
            balance_micro=pnw.balance_micro,
            portfolio_micro=pnw.portfolio_micro,
        )
        for idx, (pnw, username) in enumerate(rows)
    ]

    return LeaderboardResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/leaderboard/me", response_model=MyRankResponse)
async def get_my_rank(
    player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated player's rank and net worth breakdown."""
    result = await db.execute(
        select(PlayerNetWorth).where(
            PlayerNetWorth.player_id == player.id
        )
    )
    pnw = result.scalar_one_or_none()

    if pnw is None:
        return MyRankResponse(
            rank=None,
            player_id=player.id,
            score_micro=0,
            net_worth_micro=0,
            balance_micro=0,
            portfolio_micro=0,
            last_active_tick=0,
            updated_at_tick=0,
        )

    # Compute rank: count non-AI players with higher score
    rank_result = await db.execute(
        select(func.count(PlayerNetWorth.player_id))
        .join(Player, PlayerNetWorth.player_id == Player.id)
        .where(
            Player.is_ai == False,  # noqa: E712
            PlayerNetWorth.score_micro > pnw.score_micro,
        )
    )
    rank = rank_result.scalar_one() + 1

    return MyRankResponse(
        rank=rank,
        player_id=player.id,
        score_micro=pnw.score_micro,
        net_worth_micro=pnw.net_worth_micro,
        balance_micro=pnw.balance_micro,
        portfolio_micro=pnw.portfolio_micro,
        last_active_tick=pnw.last_active_tick,
        updated_at_tick=pnw.updated_at_tick,
    )


@router.get("/seasons", response_model=list[SeasonResponse])
async def list_seasons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all seasons, newest first."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Season)
        .order_by(Season.season_number.desc())
        .offset(offset)
        .limit(page_size)
    )
    seasons = result.scalars().all()

    return [
        SeasonResponse(
            id=s.id,
            season_number=s.season_number,
            start_tick=s.start_tick,
            end_tick=s.end_tick,
            status=s.status.value,
        )
        for s in seasons
    ]


@router.get("/seasons/current", response_model=SeasonResponse)
async def get_current_season(
    db: AsyncSession = Depends(get_db),
):
    """Get the current active season."""
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.ACTIVE)
    )
    season = result.scalar_one_or_none()

    if season is None:
        raise HTTPException(status_code=404, detail="No active season")

    return SeasonResponse(
        id=season.id,
        season_number=season.season_number,
        start_tick=season.start_tick,
        end_tick=season.end_tick,
        status=season.status.value,
    )