import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.admin import ParamValueType, SimulationParameter
from app.models.guild import Guild
from app.models.ledger import AccountEntityType, LedgerEntry
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount

logger = structlog.get_logger()

PAUSE_KEY = "simulation:paused"

# ── Tunable parameter registry ──
# key → (value_type, description)
# Only gameplay/runtime tunables — never secrets or infra config.

TUNABLE_PARAMS: dict[str, tuple[ParamValueType, str]] = {
    "system_spawn_probability": (ParamValueType.FLOAT, "Probability of system gate spawn per tick"),
    "gate_offering_ticks": (ParamValueType.INT, "Ticks a gate stays in OFFERING state"),
    "gate_base_decay_rate": (ParamValueType.FLOAT, "Base stability decay per tick"),
    "base_fee_rate": (ParamValueType.FLOAT, "Minimum trade fee rate"),
    "progressive_fee_rate": (ParamValueType.FLOAT, "Fee scaling factor for large orders"),
    "fee_scale_micro": (ParamValueType.INT, "Progressive fee denominator (micro-units)"),
    "max_fee_rate": (ParamValueType.FLOAT, "Hard cap on trade fee rate"),
    "iso_payback_ticks": (ParamValueType.INT, "Ticks of yield used to price ISO shares"),
    "guild_creation_cost_micro": (ParamValueType.INT, "Cost to create a guild (micro-units)"),
    "guild_total_shares": (ParamValueType.INT, "Total shares per guild"),
    "guild_max_float_pct": (ParamValueType.FLOAT, "Maximum public float percentage"),
    "guild_base_maintenance_micro": (ParamValueType.INT, "Base guild maintenance cost per tick"),
    "guild_maintenance_scale": (ParamValueType.FLOAT, "Maintenance cost scaling on gate value"),
    "guild_insolvency_threshold": (ParamValueType.INT, "Missed maintenance ticks before INSOLVENT"),
    "guild_dissolution_threshold": (ParamValueType.INT, "Insolvent ticks before DISSOLVED"),
    "guild_liquidation_discount": (ParamValueType.FLOAT, "Liquidation price discount factor"),
    "ai_mm_spread": (ParamValueType.FLOAT, "Market maker bid/ask spread"),
    "ai_mm_order_qty": (ParamValueType.INT, "Shares per market maker order"),
    "ai_vi_buy_discount": (ParamValueType.FLOAT, "Value investor buy discount threshold"),
    "ai_vi_sell_premium": (ParamValueType.FLOAT, "Value investor sell premium threshold"),
    "ai_noise_activity": (ParamValueType.FLOAT, "Noise trader action probability per tick"),
    "ai_noise_max_qty": (ParamValueType.INT, "Max shares per noise trade"),
    "event_probability": (ParamValueType.FLOAT, "Event chance per tick"),
    "event_stability_surge_min": (ParamValueType.FLOAT, "Min stability surge amount"),
    "event_stability_surge_max": (ParamValueType.FLOAT, "Max stability surge amount"),
    "event_stability_crisis_min": (ParamValueType.FLOAT, "Min stability crisis amount"),
    "event_stability_crisis_max": (ParamValueType.FLOAT, "Max stability crisis amount"),
    "event_market_shock_min": (ParamValueType.FLOAT, "Min market shock stability amount"),
    "event_market_shock_max": (ParamValueType.FLOAT, "Max market shock stability amount"),
    "event_yield_boom_min_multiplier": (ParamValueType.FLOAT, "Min yield boom multiplier"),
    "event_yield_boom_max_multiplier": (ParamValueType.FLOAT, "Max yield boom multiplier"),
    "event_discovery_surge_min": (ParamValueType.INT, "Min extra gates from discovery surge"),
    "event_discovery_surge_max": (ParamValueType.INT, "Max extra gates from discovery surge"),
    "news_large_trade_threshold_micro": (ParamValueType.INT, "Trade size threshold for news"),
    "portfolio_maintenance_rate": (
        ParamValueType.FLOAT,
        "Portfolio maintenance charge rate per tick",
    ),
    "concentration_threshold_pct": (
        ParamValueType.FLOAT,
        "Ownership threshold for concentration penalty",
    ),
    "concentration_penalty_rate": (
        ParamValueType.FLOAT,
        "Concentration penalty charge rate per tick",
    ),
    "liquidity_decay_inactive_ticks": (ParamValueType.INT, "Ticks without trade before decay"),
    "liquidity_decay_rate": (ParamValueType.FLOAT, "Liquidity decay charge rate per tick"),
    "max_player_ownership_pct": (ParamValueType.FLOAT, "Max ownership pct of any gate"),
    "net_worth_update_interval": (ParamValueType.INT, "Update leaderboard every N ticks"),
    "leaderboard_size": (ParamValueType.INT, "Max leaderboard entries returned"),
    "leaderboard_decay_rate": (ParamValueType.FLOAT, "Score decay rate per inactive tick"),
    "leaderboard_decay_inactive_ticks": (ParamValueType.INT, "Grace period before score decay"),
    "leaderboard_decay_floor": (ParamValueType.FLOAT, "Min decay multiplier"),
    "season_duration_ticks": (ParamValueType.INT, "Ticks per season"),
    "simulation_tick_interval": (ParamValueType.INT, "Seconds between simulation ticks"),
}

PARAM_BOUNDS: dict[str, tuple[float | None, float | None]] = {
    "system_spawn_probability": (0.0, 1.0),
    "gate_offering_ticks": (1, None),
    "gate_base_decay_rate": (0.0, None),
    "base_fee_rate": (0.0, 1.0),
    "progressive_fee_rate": (0.0, None),
    "fee_scale_micro": (1, None),
    "max_fee_rate": (0.0, 1.0),
    "iso_payback_ticks": (1, None),
    "guild_creation_cost_micro": (0, None),
    "guild_total_shares": (1, None),
    "guild_max_float_pct": (0.0, 1.0),
    "guild_base_maintenance_micro": (0, None),
    "guild_maintenance_scale": (0.0, None),
    "guild_insolvency_threshold": (1, None),
    "guild_dissolution_threshold": (1, None),
    "guild_liquidation_discount": (0.0, 1.0),
    "ai_mm_spread": (0.0, 1.0),
    "ai_mm_order_qty": (1, None),
    "ai_vi_buy_discount": (0.0, 1.0),
    "ai_vi_sell_premium": (0.0, None),
    "ai_noise_activity": (0.0, 1.0),
    "ai_noise_max_qty": (1, None),
    "event_probability": (0.0, 1.0),
    "event_stability_surge_min": (0.0, None),
    "event_stability_surge_max": (0.0, None),
    "event_stability_crisis_min": (0.0, None),
    "event_stability_crisis_max": (0.0, None),
    "event_market_shock_min": (0.0, None),
    "event_market_shock_max": (0.0, None),
    "event_yield_boom_min_multiplier": (0.0, None),
    "event_yield_boom_max_multiplier": (0.0, None),
    "event_discovery_surge_min": (0, None),
    "event_discovery_surge_max": (0, None),
    "news_large_trade_threshold_micro": (0, None),
    "portfolio_maintenance_rate": (0.0, 1.0),
    "concentration_threshold_pct": (0.0, 1.0),
    "concentration_penalty_rate": (0.0, 1.0),
    "liquidity_decay_inactive_ticks": (1, None),
    "liquidity_decay_rate": (0.0, 1.0),
    "max_player_ownership_pct": (0.0, 1.0),
    "net_worth_update_interval": (1, None),
    "leaderboard_size": (1, None),
    "leaderboard_decay_rate": (0.0, 1.0),
    "leaderboard_decay_inactive_ticks": (0, None),
    "leaderboard_decay_floor": (0.0, 1.0),
    "season_duration_ticks": (1, None),
    "simulation_tick_interval": (1, None),
}

ORDERED_PARAM_PAIRS = (
    ("event_stability_surge_min", "event_stability_surge_max"),
    ("event_stability_crisis_min", "event_stability_crisis_max"),
    ("event_market_shock_min", "event_market_shock_max"),
    ("event_yield_boom_min_multiplier", "event_yield_boom_max_multiplier"),
    ("event_discovery_surge_min", "event_discovery_surge_max"),
)


# ── Value casting helpers ──


def _cast_value(raw: str, value_type: ParamValueType) -> Any:
    if value_type == ParamValueType.INT:
        return int(raw)
    if value_type == ParamValueType.FLOAT:
        return float(raw)
    if value_type == ParamValueType.BOOL:
        return raw.lower() in ("true", "1", "yes")
    return raw


def _serialize_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _validate_bounds(key: str, value: Any) -> None:
    bounds = PARAM_BOUNDS.get(key)
    if bounds is None or not isinstance(value, (int, float)):
        return

    min_value, max_value = bounds
    if min_value is not None and value < min_value:
        raise ValueError(f"{key} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{key} must be <= {max_value}")


async def _validate_ordered_pairs(
    session: AsyncSession, key: str, value: Any
) -> None:
    affected_pairs = [pair for pair in ORDERED_PARAM_PAIRS if key in pair]
    if not affected_pairs:
        return

    result = await session.execute(select(SimulationParameter))
    effective_values: dict[str, Any] = {}
    for param in result.scalars().all():
        if param.key in TUNABLE_PARAMS:
            effective_values[param.key] = _cast_value(
                param.value, param.value_type
            )
    effective_values[key] = value

    for min_key, max_key in affected_pairs:
        min_value = effective_values.get(min_key)
        max_value = effective_values.get(max_key)
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError(f"{min_key} must be <= {max_key}")


# ── Parameter operations ──


async def seed_parameters(session: AsyncSession) -> int:
    """Seed simulation_parameters from current settings. Idempotent."""
    result = await session.execute(select(SimulationParameter.key))
    existing = {row[0] for row in result.all()}

    created = 0
    for key, (value_type, description) in TUNABLE_PARAMS.items():
        if key in existing:
            continue
        current_value = getattr(settings, key)
        param = SimulationParameter(
            key=key,
            value=_serialize_value(current_value),
            value_type=value_type,
            description=description,
        )
        session.add(param)
        created += 1

    if created > 0:
        await session.flush()
    return created


async def list_parameters(session: AsyncSession) -> list[SimulationParameter]:
    result = await session.execute(
        select(SimulationParameter).order_by(SimulationParameter.key)
    )
    return list(result.scalars().all())


async def update_parameter(
    session: AsyncSession,
    key: str,
    raw_value: str,
    updated_by: uuid.UUID,
) -> SimulationParameter:
    if key not in TUNABLE_PARAMS:
        raise ValueError(f"Unknown parameter: {key}")

    value_type = TUNABLE_PARAMS[key][0]

    try:
        typed_value = _cast_value(raw_value, value_type)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid value for {key} ({value_type.value}): {e}")

    _validate_bounds(key, typed_value)
    await _validate_ordered_pairs(session, key, typed_value)

    result = await session.execute(
        select(SimulationParameter)
        .where(SimulationParameter.key == key)
        .with_for_update()
    )
    param = result.scalar_one_or_none()
    if param is None:
        raise ValueError(f"Parameter not seeded: {key}")

    param.value = _serialize_value(typed_value)
    param.updated_at = datetime.now(UTC)
    param.updated_by = updated_by

    # Apply to in-memory settings (this process only)
    setattr(settings, key, typed_value)

    return param


async def load_parameters_into_settings(session: AsyncSession) -> None:
    """Load all parameters from DB into settings singleton.

    Called at tick start by worker to pick up admin changes.
    """
    result = await session.execute(select(SimulationParameter))
    for param in result.scalars().all():
        if param.key in TUNABLE_PARAMS:
            typed_value = _cast_value(param.value, param.value_type)
            setattr(settings, param.key, typed_value)


# ── Conservation audit ──


async def run_conservation_audit(session: AsyncSession) -> dict:
    result = await session.execute(
        select(SystemAccount.balance_micro).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury_balance = result.scalar_one()

    result = await session.execute(
        select(func.coalesce(func.sum(Player.balance_micro), 0))
    )
    player_sum = result.scalar_one()

    result = await session.execute(
        select(func.coalesce(func.sum(Guild.treasury_micro), 0))
    )
    guild_sum = result.scalar_one()

    total = treasury_balance + player_sum + guild_sum
    expected = settings.initial_seed_micro
    delta = total - expected

    return {
        "status": "PASS" if delta == 0 else "FAIL",
        "treasury_balance_micro": treasury_balance,
        "player_sum_micro": player_sum,
        "guild_sum_micro": guild_sum,
        "total_micro": total,
        "expected_micro": expected,
        "delta_micro": delta,
    }


# ── Treasury info ──


async def get_treasury_info(
    session: AsyncSession, limit: int = 20
) -> dict:
    result = await session.execute(
        select(SystemAccount).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    treasury = result.scalar_one()

    result = await session.execute(
        select(LedgerEntry)
        .where(
            ((LedgerEntry.debit_type == AccountEntityType.SYSTEM)
             & (LedgerEntry.debit_id == treasury.id))
            | ((LedgerEntry.credit_type == AccountEntityType.SYSTEM)
               & (LedgerEntry.credit_id == treasury.id))
        )
        .order_by(LedgerEntry.id.desc())
        .limit(limit)
    )
    entries = list(result.scalars().all())

    return {
        "treasury_id": treasury.id,
        "balance_micro": treasury.balance_micro,
        "recent_entries": entries,
    }
