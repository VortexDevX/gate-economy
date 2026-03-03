from datetime import datetime

from pydantic import BaseModel


class SimulationStatus(BaseModel):
    current_tick: int
    last_completed_at: datetime | None = None
    is_running: bool
    treasury_balance: int