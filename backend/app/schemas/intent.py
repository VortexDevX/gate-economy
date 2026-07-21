import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.gate import GateRank
from app.models.guild import DividendPolicy
from app.models.intent import IntentStatus, IntentType
from app.models.market import AssetType, OrderSide

PositiveStrictInt = Annotated[StrictInt, Field(gt=0)]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _IntentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscoverGatePayload(_IntentPayload):
    min_rank: GateRank


class PlaceOrderPayload(_IntentPayload):
    asset_type: AssetType
    asset_id: uuid.UUID
    side: OrderSide
    quantity: PositiveStrictInt
    price_limit_micro: PositiveStrictInt


class CancelOrderPayload(_IntentPayload):
    order_id: uuid.UUID


class CreateGuildPayload(_IntentPayload):
    name: NonEmptyString
    public_float_pct: float = Field(default=0.0, ge=0.0, le=0.49)
    dividend_policy: DividendPolicy = DividendPolicy.MANUAL
    auto_dividend_pct: float | None = Field(default=None, gt=0.0, le=1.0)

    @field_validator("public_float_pct", "auto_dividend_pct", mode="before")
    @classmethod
    def require_json_number(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a JSON number")
        return value

    @model_validator(mode="after")
    def validate_auto_dividend_policy(self) -> "CreateGuildPayload":
        if self.dividend_policy == DividendPolicy.AUTO_FIXED_PCT:
            if self.auto_dividend_pct is None:
                raise ValueError("auto_dividend_pct is required for AUTO_FIXED_PCT policy")
        elif "auto_dividend_pct" in self.model_fields_set:
            raise ValueError("auto_dividend_pct is only valid for AUTO_FIXED_PCT policy")
        return self


class GuildDividendPayload(_IntentPayload):
    guild_id: uuid.UUID
    amount_micro: PositiveStrictInt | None = None


class GuildInvestPayload(_IntentPayload):
    guild_id: uuid.UUID
    gate_id: uuid.UUID
    quantity: PositiveStrictInt
    price_limit_micro: PositiveStrictInt


INTENT_PAYLOAD_MODELS: dict[IntentType, type[_IntentPayload]] = {
    IntentType.DISCOVER_GATE: DiscoverGatePayload,
    IntentType.PLACE_ORDER: PlaceOrderPayload,
    IntentType.CANCEL_ORDER: CancelOrderPayload,
    IntentType.CREATE_GUILD: CreateGuildPayload,
    IntentType.GUILD_DIVIDEND: GuildDividendPayload,
    IntentType.GUILD_INVEST: GuildInvestPayload,
}


class IntentCreate(BaseModel):
    intent_type: IntentType
    payload: dict[str, Any]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_payload_for_intent_type(self) -> "IntentCreate":
        payload_model = INTENT_PAYLOAD_MODELS[self.intent_type]
        validated = payload_model.model_validate(self.payload)
        self.payload = validated.model_dump(mode="json", exclude_none=True)
        return self


class IntentResponse(BaseModel):
    id: uuid.UUID
    intent_type: IntentType
    status: IntentStatus
    reject_reason: str | None = None
    created_at: datetime
    processed_tick: int | None = None

    model_config = ConfigDict(from_attributes=True)


class IntentListResponse(BaseModel):
    items: list[IntentResponse]
    total: int
