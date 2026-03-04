"""Market system simulation-level tests.

Tests order placement, cancellation, matching, ISO flow,
and conservation invariant with market operations.
"""

import pytest
from sqlalchemy import and_, func, select

from app.config import settings
from app.models.gate import (
    DiscoveryType,
    Gate,
    GateRank,
    GateRankProfile,
    GateShare,
    GateStatus,
)
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.market import Order, OrderSide, OrderStatus, Trade
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.fee_calculator import calculate_escrow, calculate_fee
from app.services.order_matching import calculate_iso_price
from app.simulation.tick import execute_tick


# ── Disable system spawns for all tests in this module ──


@pytest.fixture(autouse=True)
def _no_system_spawn():
    orig = settings.system_spawn_probability
    settings.system_spawn_probability = 0.0
    yield
    settings.system_spawn_probability = orig


# ── Helpers ──


async def _treasury_id(sf):
    async with sf() as s:
        r = await s.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        return r.scalar_one()


async def _active_gate(sf, t_id, owner_id=None, qty=100):
    """Create ACTIVE E-rank gate with 0 yield. Shares to owner_id or treasury."""
    async with sf() as s:
        g = Gate(
            rank=GateRank.E, stability=90.0, volatility=0.05,
            base_yield_micro=0, total_shares=qty,
            status=GateStatus.ACTIVE, spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        s.add(g)
        await s.flush()
        s.add(GateShare(gate_id=g.id, player_id=owner_id or t_id, quantity=qty))
        await s.commit()
        return g.id


async def _offering_gate(sf, t_id, qty=100):
    """Create OFFERING E-rank gate. All shares with treasury."""
    async with sf() as s:
        g = Gate(
            rank=GateRank.E, stability=100.0, volatility=0.05,
            base_yield_micro=0, total_shares=qty,
            status=GateStatus.OFFERING, spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        s.add(g)
        await s.flush()
        s.add(GateShare(gate_id=g.id, player_id=t_id, quantity=qty))
        await s.commit()
        return g.id


async def _queue(sf, pid, payload):
    """Queue a PLACE_ORDER intent, return intent ID."""
    async with sf() as s:
        i = Intent(
            player_id=pid, intent_type=IntentType.PLACE_ORDER,
            payload=payload, status=IntentStatus.QUEUED,
        )
        s.add(i)
        await s.commit()
        return i.id


async def _queue_cancel(sf, pid, order_id):
    """Queue a CANCEL_ORDER intent, return intent ID."""
    async with sf() as s:
        i = Intent(
            player_id=pid, intent_type=IntentType.CANCEL_ORDER,
            payload={"order_id": str(order_id)},
            status=IntentStatus.QUEUED,
        )
        s.add(i)
        await s.commit()
        return i.id


def _pay(gid, side, qty, price):
    """Build PLACE_ORDER payload dict."""
    return {
        "asset_type": "GATE_SHARE", "asset_id": str(gid),
        "side": side, "quantity": qty, "price_limit_micro": price,
    }


async def _balance(sf, pid):
    async with sf() as s:
        r = await s.execute(select(Player.balance_micro).where(Player.id == pid))
        return r.scalar_one()


async def _shares(sf, gid, pid):
    async with sf() as s:
        r = await s.execute(
            select(GateShare.quantity).where(
                and_(GateShare.gate_id == gid, GateShare.player_id == pid)
            )
        )
        return r.scalar_one_or_none() or 0


# ── Order Placement ──


@pytest.mark.asyncio
async def test_buy_order_escrows_funds(session_factory, pause_simulation, funded_player_id):
    """BUY order deducts escrow (cost + max fee) from player."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)
    bal0 = await _balance(session_factory, funded_player_id)
    qty, price = 5, 50_000
    escrow, _ = calculate_escrow(qty, price)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", qty, price))
    await execute_tick(session_factory)

    assert await _balance(session_factory, funded_player_id) == bal0 - escrow
    async with session_factory() as s:
        r = await s.execute(select(Order).where(Order.player_id == funded_player_id))
        o = r.scalar_one()
        assert o.status == OrderStatus.OPEN
        assert o.escrow_micro == escrow


@pytest.mark.asyncio
async def test_sell_order_created(session_factory, pause_simulation, funded_player_id):
    """SELL order created when player owns shares. No escrow."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=funded_player_id, qty=50)
    bal0 = await _balance(session_factory, funded_player_id)

    await _queue(session_factory, funded_player_id, _pay(gid, "SELL", 10, 100_000))
    await execute_tick(session_factory)

    assert await _balance(session_factory, funded_player_id) == bal0
    async with session_factory() as s:
        r = await s.execute(select(Order).where(Order.player_id == funded_player_id))
        o = r.scalar_one()
        assert o.status == OrderStatus.OPEN
        assert o.side == OrderSide.SELL
        assert o.escrow_micro == 0


@pytest.mark.asyncio
async def test_sell_rejected_insufficient_shares(
    session_factory, pause_simulation, funded_player_id,
):
    """SELL rejected when player owns no shares of the asset."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)

    iid = await _queue(session_factory, funded_player_id, _pay(gid, "SELL", 10, 50_000))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Intent).where(Intent.id == iid))
        assert r.scalar_one().status == IntentStatus.REJECTED


@pytest.mark.asyncio
async def test_buy_rejected_insufficient_balance(
    session_factory, pause_simulation, test_player_id,
):
    """BUY rejected when player has 0 balance."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)

    iid = await _queue(session_factory, test_player_id, _pay(gid, "BUY", 10, 100_000))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Intent).where(Intent.id == iid))
        assert r.scalar_one().status == IntentStatus.REJECTED


@pytest.mark.asyncio
async def test_double_sell_rejected(session_factory, pause_simulation, funded_player_id):
    """Second SELL rejected when it over-commits available shares."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=funded_player_id, qty=10)

    await _queue(session_factory, funded_player_id, _pay(gid, "SELL", 8, 50_000))
    iid = await _queue(session_factory, funded_player_id, _pay(gid, "SELL", 5, 50_000))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Intent).where(Intent.id == iid))
        assert r.scalar_one().status == IntentStatus.REJECTED
        r = await s.execute(select(Order).where(
            and_(Order.player_id == funded_player_id, Order.status == OrderStatus.OPEN)
        ))
        assert r.scalar_one().quantity == 8


# ── Cancellation ──


@pytest.mark.asyncio
async def test_cancel_buy_releases_escrow(
    session_factory, pause_simulation, funded_player_id,
):
    """Cancelling BUY order returns full escrow to player."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)
    bal0 = await _balance(session_factory, funded_player_id)
    qty, price = 5, 50_000
    escrow, _ = calculate_escrow(qty, price)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", qty, price))
    await execute_tick(session_factory)
    assert await _balance(session_factory, funded_player_id) == bal0 - escrow

    async with session_factory() as s:
        r = await s.execute(select(Order.id).where(Order.player_id == funded_player_id))
        oid = r.scalar_one()

    await _queue_cancel(session_factory, funded_player_id, oid)
    await execute_tick(session_factory)

    assert await _balance(session_factory, funded_player_id) == bal0
    async with session_factory() as s:
        r = await s.execute(select(Order).where(Order.id == oid))
        assert r.scalar_one().status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_sell_order(session_factory, pause_simulation, funded_player_id):
    """Cancelling SELL order sets CANCELLED, no balance change."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=funded_player_id, qty=20)
    bal0 = await _balance(session_factory, funded_player_id)

    await _queue(session_factory, funded_player_id, _pay(gid, "SELL", 10, 50_000))
    await execute_tick(session_factory)
    async with session_factory() as s:
        r = await s.execute(select(Order.id).where(Order.player_id == funded_player_id))
        oid = r.scalar_one()

    await _queue_cancel(session_factory, funded_player_id, oid)
    await execute_tick(session_factory)

    assert await _balance(session_factory, funded_player_id) == bal0
    async with session_factory() as s:
        r = await s.execute(select(Order).where(Order.id == oid))
        assert r.scalar_one().status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_wrong_player_rejected(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """Cannot cancel another player's order."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 1, 50_000))
    await execute_tick(session_factory)
    async with session_factory() as s:
        r = await s.execute(select(Order.id).where(Order.player_id == funded_player_id))
        oid = r.scalar_one()

    iid = await _queue_cancel(session_factory, test_player_id, oid)
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Intent).where(Intent.id == iid))
        assert r.scalar_one().status == IntentStatus.REJECTED
        r = await s.execute(select(Order).where(Order.id == oid))
        assert r.scalar_one().status == OrderStatus.OPEN


# ── Matching ──


@pytest.mark.asyncio
async def test_basic_match(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """Compatible BUY + SELL produces trade at maker (seller) price."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=test_player_id, qty=100)

    qty, sell_price, buy_price = 10, 50_000, 60_000
    await _queue(session_factory, test_player_id, _pay(gid, "SELL", qty, sell_price))
    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", qty, buy_price))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Trade))
        trade = r.scalar_one()
        assert trade.quantity == qty
        assert trade.price_micro == sell_price
        assert trade.buyer_fee_micro > 0
        assert trade.seller_fee_micro > 0
    assert await _shares(session_factory, gid, test_player_id) == 90
    assert await _shares(session_factory, gid, funded_player_id) == 10


@pytest.mark.asyncio
async def test_no_match_when_prices_dont_cross(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """BUY below SELL price produces no trade, both stay OPEN."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=test_player_id, qty=100)

    await _queue(session_factory, test_player_id, _pay(gid, "SELL", 10, 100_000))
    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 10, 50_000))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(func.count(Trade.id)))
        assert r.scalar_one() == 0
        r = await s.execute(select(Order).where(Order.status == OrderStatus.OPEN))
        assert len(r.scalars().all()) == 2


@pytest.mark.asyncio
async def test_partial_fill(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """BUY for 20 against SELL for 5 produces partial fill on BUY."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=test_player_id, qty=100)

    await _queue(session_factory, test_player_id, _pay(gid, "SELL", 5, 50_000))
    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 20, 60_000))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Order).where(
            and_(Order.side == OrderSide.BUY, Order.is_system.is_(False))
        ))
        buy = r.scalar_one()
        assert buy.status == OrderStatus.PARTIAL
        assert buy.filled_quantity == 5
        assert buy.escrow_micro > 0


@pytest.mark.asyncio
async def test_excess_escrow_released_on_fill(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """Full fill at lower-than-limit price releases excess escrow."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=test_player_id, qty=100)
    bal0 = await _balance(session_factory, funded_player_id)

    qty, sell_price, buy_price = 10, 30_000, 100_000
    await _queue(session_factory, test_player_id, _pay(gid, "SELL", qty, sell_price))
    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", qty, buy_price))
    await execute_tick(session_factory)

    trade_value = qty * sell_price
    buyer_fee = calculate_fee(trade_value)
    assert await _balance(session_factory, funded_player_id) == bal0 - trade_value - buyer_fee
    async with session_factory() as s:
        r = await s.execute(select(Order).where(
            and_(Order.side == OrderSide.BUY, Order.is_system.is_(False))
        ))
        assert r.scalar_one().escrow_micro == 0


@pytest.mark.asyncio
async def test_collapsed_gate_orders_cancelled(
    session_factory, pause_simulation, funded_player_id,
):
    """Orders on collapsed gates are cancelled, BUY escrow released."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id)
    bal0 = await _balance(session_factory, funded_player_id)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 5, 50_000))
    await execute_tick(session_factory)
    assert await _balance(session_factory, funded_player_id) < bal0

    async with session_factory() as s:
        r = await s.execute(select(Gate).where(Gate.id == gid).with_for_update())
        r.scalar_one().status = GateStatus.COLLAPSED
        await s.commit()

    await execute_tick(session_factory)
    assert await _balance(session_factory, funded_player_id) == bal0
    async with session_factory() as s:
        r = await s.execute(select(Order).where(Order.player_id == funded_player_id))
        assert r.scalar_one().status == OrderStatus.CANCELLED


# ── ISO ──


@pytest.mark.asyncio
async def test_iso_creates_and_matches(
    session_factory, pause_simulation, funded_player_id,
):
    """ISO order created for OFFERING gate, matches BUY, no seller fee,
    gate transitions ACTIVE when all shares sold."""
    t_id = await _treasury_id(session_factory)
    qty = 10
    gid = await _offering_gate(session_factory, t_id, qty=qty)

    async with session_factory() as s:
        r = await s.execute(
            select(GateRankProfile).where(GateRankProfile.rank == GateRank.E)
        )
        profile = r.scalar_one()
    iso_price = calculate_iso_price(profile)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", qty, iso_price))
    await execute_tick(session_factory)

    async with session_factory() as s:
        r = await s.execute(select(Trade))
        trade = r.scalar_one()
        assert trade.quantity == qty
        assert trade.price_micro == iso_price
        assert trade.seller_fee_micro == 0
    assert await _shares(session_factory, gid, funded_player_id) == qty
    assert await _shares(session_factory, gid, t_id) == 0
    async with session_factory() as s:
        r = await s.execute(select(Gate).where(Gate.id == gid))
        assert r.scalar_one().status == GateStatus.ACTIVE


# ── Conservation ──


@pytest.mark.asyncio
async def test_conservation_after_trading(
    session_factory, pause_simulation, funded_player_id, test_player_id,
):
    """Conservation invariant holds after escrows, trades, and fees."""
    t_id = await _treasury_id(session_factory)
    gid = await _active_gate(session_factory, t_id, owner_id=test_player_id, qty=50)

    await _queue(session_factory, test_player_id, _pay(gid, "SELL", 20, 40_000))
    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 10, 50_000))
    await execute_tick(session_factory)

    await _queue(session_factory, funded_player_id, _pay(gid, "BUY", 5, 60_000))
    await execute_tick(session_factory)

    await execute_tick(session_factory)  # empty tick

    async with session_factory() as s:
        r = await s.execute(
            select(SystemAccount.balance_micro).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury = r.scalar_one()
        r = await s.execute(
            select(func.coalesce(func.sum(Player.balance_micro), 0))
        )
        players = r.scalar_one()
        assert treasury + players == settings.initial_seed_micro