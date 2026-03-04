"""Progressive fee calculator.

All functions are pure — no DB, no side effects.
Fee formula: fee_rate = base + (value / scale) * progressive_rate, capped at max.
"""

from app.config import settings


def calculate_fee(trade_value_micro: int) -> int:
    """Calculate progressive fee for a given trade value.

    Returns fee in micro-units. Always >= 0.
    """
    if trade_value_micro <= 0:
        return 0

    fee_rate = settings.base_fee_rate + (
        trade_value_micro / settings.fee_scale_micro
    ) * settings.progressive_fee_rate
    fee_rate = min(fee_rate, settings.max_fee_rate)
    return int(trade_value_micro * fee_rate)


def calculate_max_fee(max_trade_value_micro: int) -> int:
    """Maximum possible fee — used for escrow calculation.

    Same as calculate_fee since fee is monotonically increasing with value.
    """
    return calculate_fee(max_trade_value_micro)


def calculate_escrow(quantity: int, price_limit_micro: int) -> tuple[int, int]:
    """Calculate total escrow needed for a BUY order.

    Returns (total_escrow, max_fee).
    total_escrow = max_cost + max_fee.
    """
    max_cost = quantity * price_limit_micro
    max_fee = calculate_max_fee(max_cost)
    return max_cost + max_fee, max_fee