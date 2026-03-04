from app.services.fee_calculator import calculate_escrow, calculate_fee


def test_small_trade_fee():
    """Small trades pay base + small progressive component."""
    value = 100_000  # 0.1 currency
    fee = calculate_fee(value)
    # rate = 0.005 + (100_000 / 10_000_000) * 0.5 = 0.01
    assert fee == int(value * 0.01)  # 1,000


def test_medium_trade_fee():
    """Medium trades scale progressively."""
    value = 1_000_000  # 1 currency
    fee = calculate_fee(value)
    # rate = 0.005 + (1_000_000 / 10_000_000) * 0.5 = 0.055
    assert fee == int(value * 0.055)  # 55,000


def test_large_trade_fee_capped():
    """Large trades hit the max fee rate cap (10%)."""
    value = 5_000_000  # 5 currency
    fee = calculate_fee(value)
    # rate = 0.005 + 0.25 = 0.255 → capped to 0.10
    assert fee == int(value * 0.10)  # 500,000


def test_zero_value():
    """Zero trade value produces zero fee."""
    assert calculate_fee(0) == 0


def test_negative_value():
    """Negative trade value produces zero fee."""
    assert calculate_fee(-100) == 0


def test_escrow_calculation():
    """Escrow = max_cost + max_fee, both values correct."""
    qty, price = 10, 50_000
    total_escrow, max_fee = calculate_escrow(qty, price)
    max_cost = qty * price  # 500,000
    expected_fee = calculate_fee(max_cost)
    assert max_fee == expected_fee
    assert total_escrow == max_cost + expected_fee