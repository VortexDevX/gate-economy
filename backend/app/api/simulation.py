from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.tick import Tick
from app.models.treasury import AccountType, SystemAccount
from app.schemas.simulation import SimulationStatus

router = APIRouter(tags=["simulation"])

# If last tick completed within this window, simulation is considered running
_RUNNING_THRESHOLD = timedelta(seconds=30)


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
    is_running = False
    if last_tick and last_tick.completed_at:
        age = datetime.now(UTC) - last_tick.completed_at
        is_running = age < _RUNNING_THRESHOLD

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
        treasury_balance=treasury_balance,
    )