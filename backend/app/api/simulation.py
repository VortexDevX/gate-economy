from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_db
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.schemas.simulation import SimulationStatus
from app.services.admin import PAUSE_KEY

router = APIRouter(tags=["simulation"])

@router.get("/simulation/status", response_model=SimulationStatus)
async def get_simulation_status(
    db: AsyncSession = Depends(get_db),
) -> SimulationStatus:
    """Return current simulation state."""
    # Last completed tick
    result = await db.execute(
        select(Tick)
        .where(Tick.completed_at.is_not(None))
        .order_by(Tick.tick_number.desc())
        .limit(1)
    )
    last_tick = result.scalar_one_or_none()

    # Is the simulation actively producing ticks?
    # Use a dynamic threshold to avoid false "stopped" status when interval is tuned.
    threshold_seconds = max(30, int(settings.simulation_tick_interval) * 3)
    running_threshold = timedelta(seconds=threshold_seconds)
    is_running = False
    if last_tick and last_tick.completed_at:
        age = datetime.now(UTC) - last_tick.completed_at
        is_running = age < running_threshold

    # Is simulation explicitly paused by admin controls?
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        is_paused = bool(await redis.get(PAUSE_KEY))
    finally:
        await redis.aclose()

    # Treasury balance
    result = await db.execute(
        select(SystemAccount.balance_micro).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury_balance = result.scalar_one()

    return SimulationStatus(
        current_tick=last_tick.tick_number if last_tick else 0,
        last_completed_at=last_tick.completed_at if last_tick else None,
        is_running=is_running,
        is_paused=is_paused,
        treasury_balance=treasury_balance,
    )
