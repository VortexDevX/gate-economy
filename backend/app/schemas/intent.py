import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.intent import IntentStatus, IntentType


class IntentCreate(BaseModel):
    intent_type: IntentType
    payload: dict


class IntentResponse(BaseModel):
    id: uuid.UUID
    intent_type: IntentType
    status: IntentStatus
    reject_reason: str | None = None
    created_at: datetime
    processed_tick: int | None = None

    model_config = ConfigDict(from_attributes=True)