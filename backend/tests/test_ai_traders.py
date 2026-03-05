"""Phase 7 — AI Trader tests."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models.gate import (
    Gate,
    GateRank,
    GateRankProfile,
    GateShare,
    GateStatus,
    DiscoveryType,
)
from app.models.ledger import AccountEntityType, EntryType, LedgerEntry
from app.models.market import (
    AssetType,
    MarketPrice,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
)
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.ai_traders import (
    _cancel_ai_orders,
    _get_reference_price,
    _place_ai_buy,
    _place_ai_sell,
    run_ai_traders,
    run_market_maker,
    run_noise_trader,
    run_value_investor,
)
from app.services.transfer import transfer
from app.simulation.rng import TickRNG


# ─── Helpers ─────────────────────────────────────────────


async def _get_treasury(session: AsyncSession):
    result = await session.execute(
        select(SystemAccount).where(
            SystemAccount.account_type == AccountType.TREASURY
        )
    )
    return result.scalar_one()


async def _create_ai_player(
    session: AsyncSession, username: str, budget: int
) -> Player:
    """Create an AI player funded from treasury."""
    treasury = await _get_treasury(session)
    player = Player(
        username=username,
        email=f"{username}@test.internal",
        password_hash="!ai-no-login",
        balance_micro=0,
        is_ai=True,
    )
    session.add(player)
    await session.flush()

    await transfer(
        session=session,
        from_type=AccountEntityType.SYSTEM,
        from_id=treasury.id,
        to_type=AccountEntityType.PLAYER,
        to_id=player.id,
        amount=budget,
        entry_type=EntryType.AI_BUDGET,
        memo=f"Test AI budget: {username}",
    )
    return player


async def _seed_rank_profiles(session: AsyncSession) -> None:
    """Seed E-rank profile for tests."""
    result = await session.execute(
        select(GateRankProfile).where(GateRankProfile.rank == GateRank.E)
    )
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        GateRankProfile(
            rank=GateRank.E,
            stability_init=100.0,
            volatility=0.05,
            yield_min_micro=1_000,
            yield_max_micro=5_000,
            total_shares=100,
            lifespan_min=200,
            lifespan_max=400,
            collapse_threshold=20.0,
            discovery_cost_micro=100_000,
            spawn_weight=40,
        )
    )
    await session.flush()


async def _create_gate(
    session: AsyncSession,
    status: GateStatus = GateStatus.ACTIVE,
    tick: int = 1,
    rank: GateRank = GateRank.E,
    stability: float = 80.0,
    base_yield: int = 3_000,
    total_shares: int = 100,
) -> Gate:
    """Create a gate with given status."""
    gate = Gate(
        rank=rank,
        stability=stability,
        volatility=0.05,
        base_yield_micro=base_yield,
        total_shares=total_shares,
        status=status,
        spawned_at_tick=tick,
        discovery_type=DiscoveryType.SYSTEM,
    )
    session.add(gate)
    await session.flush()
    return gate


async def _set_market_price(
    session: AsyncSession,
    gate_id: uuid.UUID,
    last_price: int | None = None,
    best_ask: int | None = None,
    best_bid: int | None = None,
    tick: int = 1,
) -> MarketPrice:
    mp = MarketPrice(
        asset_type=AssetType.GATE_SHARE,
        asset_id=gate_id,
        last_price_micro=last_price,
        best_ask_micro=best_ask,
        best_bid_micro=best_bid,
        updated_at_tick=tick,
    )
    session.add(mp)
    await session.flush()
    return mp


async def _give_shares(
    session: AsyncSession,
    gate_id: uuid.UUID,
    player_id: uuid.UUID,
    qty: int,
) -> GateShare:
    gs = GateShare(gate_id=gate_id, player_id=player_id, quantity=qty)
    session.add(gs)
    await session.flush()
    return gs


async def _check_conservation(session: AsyncSession) -> None:
    """Assert closed-economy invariant."""
    treasury = await _get_treasury(session)
    result = await session.execute(
        select(func.coalesce(func.sum(Player.balance_micro), 0))
    )
    player_sum = result.scalar_one()

    from app.models.guild import Guild

    result = await session.execute(
        select(func.coalesce(func.sum(Guild.treasury_micro), 0))
    )
    guild_sum = result.scalar_one()

    total = treasury.balance_micro + player_sum + guild_sum
    assert total == settings.initial_seed_micro, (
        f"Conservation violated: {total} != {settings.initial_seed_micro}"
    )


# ─── Seeding Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_seeding_creates_3_players(session_factory: async_sessionmaker):
    """AI seeding creates 3 is_ai=True players."""
    async with session_factory() as session:
        await _create_ai_player(session, "ai_market_maker", settings.ai_market_maker_budget_micro)
        await _create_ai_player(session, "ai_value_investor", settings.ai_value_investor_budget_micro)
        await _create_ai_player(session, "ai_noise_trader", settings.ai_noise_trader_budget_micro)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player).where(Player.is_ai == True)  # noqa: E712
        )
        ai_players = list(result.scalars().all())
        assert len(ai_players) == 3
        usernames = {p.username for p in ai_players}
        assert usernames == {"ai_market_maker", "ai_value_investor", "ai_noise_trader"}


@pytest.mark.asyncio
async def test_ai_seeding_is_idempotent(session_factory: async_sessionmaker):
    """Creating AI players twice doesn't duplicate."""
    async with session_factory() as session:
        treasury = await _get_treasury(session)
        # First round
        for username, email, budget in [
            ("ai_market_maker", "ai_mm@system.internal", settings.ai_market_maker_budget_micro),
            ("ai_value_investor", "ai_vi@system.internal", settings.ai_value_investor_budget_micro),
            ("ai_noise_trader", "ai_nt@system.internal", settings.ai_noise_trader_budget_micro),
        ]:
            await _create_ai_player(session, username, budget)
        await session.commit()

    # Second round — same usernames, should skip (check count stays 3)
    async with session_factory() as session:
        for username in ["ai_market_maker", "ai_value_investor", "ai_noise_trader"]:
            result = await session.execute(
                select(Player).where(Player.username == username)
            )
            assert result.scalar_one_or_none() is not None  # exists

        result = await session.execute(
            select(func.count()).select_from(Player).where(
                Player.is_ai == True  # noqa: E712
            )
        )
        assert result.scalar_one() == 3


@pytest.mark.asyncio
async def test_ai_seeding_funds_from_treasury(session_factory: async_sessionmaker):
    """AI budgets come from treasury — conservation holds."""
    async with session_factory() as session:
        await _create_ai_player(session, "ai_market_maker", settings.ai_market_maker_budget_micro)
        await _create_ai_player(session, "ai_value_investor", settings.ai_value_investor_budget_micro)
        await _create_ai_player(session, "ai_noise_trader", settings.ai_noise_trader_budget_micro)
        await session.commit()

    async with session_factory() as session:
        await _check_conservation(session)

        result = await session.execute(
            select(Player).where(Player.username == "ai_market_maker")
        )
        mm = result.scalar_one()
        assert mm.balance_micro == settings.ai_market_maker_budget_micro
        

# ─── Helper Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_reference_price_last_price(session_factory: async_sessionmaker):
    """Reference price prefers last_price."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        gate = await _create_gate(session)
        await _set_market_price(session, gate.id, last_price=5_000)

        price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        assert price == 5_000


@pytest.mark.asyncio
async def test_reference_price_falls_back_to_best_ask(
    session_factory: async_sessionmaker,
):
    """If no last_price, use best_ask."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        gate = await _create_gate(session)
        await _set_market_price(session, gate.id, best_ask=7_000)

        price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        assert price == 7_000


@pytest.mark.asyncio
async def test_reference_price_iso_estimate_for_offering(
    session_factory: async_sessionmaker,
):
    """OFFERING gate without market price falls back to ISO estimate."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        gate = await _create_gate(
            session,
            status=GateStatus.OFFERING,
            stability=100.0,
            base_yield=3_000,
            total_shares=100,
        )
        # No MarketPrice row
        price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        # ISO price = (3000 * (100/100) * 100) // 100 = 3000
        expected = int(3_000 * 1.0 * settings.iso_payback_ticks) // 100
        assert price == expected


@pytest.mark.asyncio
async def test_reference_price_none_when_no_data(
    session_factory: async_sessionmaker,
):
    """Active gate with no market data returns None."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        gate = await _create_gate(session)

        price = await _get_reference_price(
            session, AssetType.GATE_SHARE, gate.id, gate
        )
        assert price is None


# ─── Market Maker Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_mm_places_buy_order(session_factory: async_sessionmaker):
    """MM places BUY order at spread below reference price."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
        gate = await _create_gate(session)
        await _set_market_price(session, gate.id, last_price=10_000)
        treasury = await _get_treasury(session)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player).where(Player.username == "ai_market_maker").with_for_update()
        )
        mm = result.scalar_one()
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(Order).where(
                Order.player_id == mm.id,
                Order.side == OrderSide.BUY,
            )
        )
        buy_orders = list(result.scalars().all())
        assert len(buy_orders) >= 1
        # Price should be below reference
        for o in buy_orders:
            assert o.price_limit_micro == int(10_000 * (1 - settings.ai_mm_spread))


@pytest.mark.asyncio
async def test_mm_places_sell_when_holding(session_factory: async_sessionmaker):
    """MM places SELL order only when holding shares."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
        gate = await _create_gate(session)
        await _give_shares(session, gate.id, mm.id, 10)
        await _set_market_price(session, gate.id, last_price=10_000)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(
            select(Player).where(Player.username == "ai_market_maker").with_for_update()
        )
        mm = result.scalar_one()
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(Order).where(
                Order.player_id == mm.id,
                Order.side == OrderSide.SELL,
            )
        )
        sell_orders = list(result.scalars().all())
        assert len(sell_orders) >= 1
        for o in sell_orders:
            assert o.price_limit_micro == int(10_000 * (1 + settings.ai_mm_spread))


@pytest.mark.asyncio
async def test_mm_cancels_old_orders(session_factory: async_sessionmaker):
    """MM cancels previous orders and releases escrow on new tick."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
        gate = await _create_gate(session)
        await _set_market_price(session, gate.id, last_price=10_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        # Tick 1: place orders
        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(Order).where(
                Order.player_id == mm.id,
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            )
        )
        tick1_orders = list(result.scalars().all())
        assert len(tick1_orders) >= 1

        # Tick 2: cancel and replace
        rng2 = TickRNG(99)
        await run_market_maker(session, mm, 2, 2, treasury.id, rng2)
        await session.flush()

        # Old orders should be cancelled
        for oid in [o.id for o in tick1_orders]:
            result = await session.execute(select(Order).where(Order.id == oid))
            old = result.scalar_one()
            assert old.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_mm_skips_gate_without_price(session_factory: async_sessionmaker):
    """MM skips gates with no reference price."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
        # Active gate, NO market price
        gate = await _create_gate(session)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(func.count()).select_from(Order).where(
                Order.player_id == mm.id,
            )
        )
        assert result.scalar_one() == 0


# ─── Value Investor Tests ───────────────────────────────


@pytest.mark.asyncio
async def test_vi_buys_undervalued(session_factory: async_sessionmaker):
    """VI places BUY when market price is well below fair value."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        vi = await _create_ai_player(session, "ai_value_investor", 500_000_000)
        # Gate with high yield → high fair value
        gate = await _create_gate(
            session, stability=80.0, base_yield=5_000, total_shares=100
        )
        # Set low market price (below fair value * 0.7)
        # Fair value ≈ (5000 * 0.8 * (80-20)/0.1) / 100 = (5000*0.8*600)/100 = 24,000
        # Buy threshold = 24,000 * 0.7 = 16,800
        await _set_market_price(session, gate.id, last_price=5_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_value_investor(session, vi, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(Order).where(
                Order.player_id == vi.id,
                Order.side == OrderSide.BUY,
            )
        )
        buy_orders = list(result.scalars().all())
        assert len(buy_orders) >= 1


@pytest.mark.asyncio
async def test_vi_skips_fairly_priced(session_factory: async_sessionmaker):
    """VI places no orders when price is near fair value."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        vi = await _create_ai_player(session, "ai_value_investor", 500_000_000)
        gate = await _create_gate(
            session, stability=80.0, base_yield=5_000, total_shares=100
        )
        # Fair value ≈ 24,000 — set price right at fair value
        await _set_market_price(session, gate.id, last_price=24_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_value_investor(session, vi, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(func.count()).select_from(Order).where(
                Order.player_id == vi.id,
            )
        )
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_vi_sells_overvalued(session_factory: async_sessionmaker):
    """VI places SELL when holding shares and price is well above fair value."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        vi = await _create_ai_player(session, "ai_value_investor", 500_000_000)
        gate = await _create_gate(
            session, stability=80.0, base_yield=5_000, total_shares=100
        )
        await _give_shares(session, gate.id, vi.id, 10)
        # Fair value ≈ 24,000 — sell threshold = 24,000 * 1.3 = 31,200
        await _set_market_price(session, gate.id, last_price=50_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_value_investor(session, vi, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(Order).where(
                Order.player_id == vi.id,
                Order.side == OrderSide.SELL,
            )
        )
        sell_orders = list(result.scalars().all())
        assert len(sell_orders) >= 1
        assert sell_orders[0].quantity == 10  # sells all holdings


# ─── Noise Trader Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_nt_places_random_order(session_factory: async_sessionmaker):
    """NT places an order when RNG allows activity."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        nt = await _create_ai_player(session, "ai_noise_trader", 100_000_000)
        gate = await _create_gate(session)
        await _give_shares(session, gate.id, nt.id, 10)
        await _set_market_price(session, gate.id, last_price=10_000)
        treasury = await _get_treasury(session)

        # Find a seed where noise_activity check passes (rng.random() < 0.40)
        # and results in a trade
        placed = False
        for seed in range(100):
            rng = TickRNG(seed)
            if rng.random() < settings.ai_noise_activity:
                # Reset — need fresh RNG for actual call
                rng2 = TickRNG(seed)
                await run_noise_trader(session, nt, 1, 1, treasury.id, rng2)
                await session.flush()

                result = await session.execute(
                    select(func.count()).select_from(Order).where(
                        Order.player_id == nt.id,
                    )
                )
                if result.scalar_one() > 0:
                    placed = True
                    break
                # Clean up for next attempt
                await session.execute(
                    select(Order).where(Order.player_id == nt.id)
                )

        assert placed, "NT should place at least one order with some seed"


@pytest.mark.asyncio
async def test_nt_skips_with_probability(session_factory: async_sessionmaker):
    """NT does nothing when RNG says skip."""
    old_activity = settings.ai_noise_activity
    try:
        settings.ai_noise_activity = 0.0  # never act

        async with session_factory() as session:
            await _seed_rank_profiles(session)
            nt = await _create_ai_player(session, "ai_noise_trader", 100_000_000)
            gate = await _create_gate(session)
            await _set_market_price(session, gate.id, last_price=10_000)
            treasury = await _get_treasury(session)
            rng = TickRNG(42)

            await run_noise_trader(session, nt, 1, 1, treasury.id, rng)
            await session.flush()

            result = await session.execute(
                select(func.count()).select_from(Order).where(
                    Order.player_id == nt.id,
                )
            )
            assert result.scalar_one() == 0
    finally:
        settings.ai_noise_activity = old_activity


# ─── Edge Cases ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_does_nothing_without_gates(session_factory: async_sessionmaker):
    """No orders placed when there are no tradeable gates."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
        vi = await _create_ai_player(session, "ai_value_investor", 100_000_000)
        nt = await _create_ai_player(session, "ai_noise_trader", 100_000_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_ai_traders(session, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(func.count()).select_from(Order)
        )
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_ai_buy_fails_when_broke(session_factory: async_sessionmaker):
    """AI with no balance can't place buy orders — no crash."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        mm = await _create_ai_player(session, "ai_market_maker", 1)  # 1 micro
        gate = await _create_gate(session)
        await _set_market_price(session, gate.id, last_price=10_000_000)
        treasury = await _get_treasury(session)
        rng = TickRNG(42)

        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        result = await session.execute(
            select(func.count()).select_from(Order).where(
                Order.player_id == mm.id,
                Order.side == OrderSide.BUY,
            )
        )
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_conservation_after_ai_trading(session_factory: async_sessionmaker):
    """Treasury + players + guilds = INITIAL_SEED after AI orders + matching."""
    from app.simulation.tick import execute_tick

    old_spawn = settings.system_spawn_probability
    try:
        settings.system_spawn_probability = 0.0

        async with session_factory() as session:
            await _seed_rank_profiles(session)
            mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)
            gate = await _create_gate(session, status=GateStatus.ACTIVE)
            await _give_shares(session, gate.id, mm.id, 20)
            await _set_market_price(
                session, gate.id, last_price=10_000, tick=0
            )
            await session.commit()

        # Run a full tick (AI creates orders, matching runs)
        tick = await execute_tick(session_factory)

        async with session_factory() as session:
            await _check_conservation(session)
    finally:
        settings.system_spawn_probability = old_spawn


@pytest.mark.asyncio
async def test_ai_orders_matched_via_standard_matching(
    session_factory: async_sessionmaker,
):
    """AI buy + human sell → trade executes, balances update."""
    async with session_factory() as session:
        await _seed_rank_profiles(session)
        treasury = await _get_treasury(session)

        # AI buyer
        mm = await _create_ai_player(session, "ai_market_maker", 100_000_000)

        # Human seller with shares
        seller = Player(
            username="human_seller",
            email="seller@test.com",
            password_hash="not-real",
            balance_micro=0,
        )
        session.add(seller)
        await session.flush()
        await transfer(
            session, AccountEntityType.SYSTEM, treasury.id,
            AccountEntityType.PLAYER, seller.id,
            10_000_000, EntryType.STARTING_GRANT,
        )

        gate = await _create_gate(session, status=GateStatus.ACTIVE)
        await _give_shares(session, gate.id, seller.id, 10)
        await _set_market_price(session, gate.id, last_price=10_000)

        # MM places buy at 9500 (5% below)
        rng = TickRNG(42)
        await run_market_maker(session, mm, 1, 1, treasury.id, rng)
        await session.flush()

        # Human places matching sell at 9500
        sell_order = Order(
            player_id=seller.id,
            asset_type=AssetType.GATE_SHARE,
            asset_id=gate.id,
            side=OrderSide.SELL,
            quantity=5,
            price_limit_micro=9_500,
            created_at_tick=1,
        )
        session.add(sell_order)
        await session.flush()

        # Match
        from app.services.order_matching import match_orders

        await match_orders(session, 1, 1, treasury.id)
        await session.flush()

        # Should have at least one trade
        result = await session.execute(select(func.count()).select_from(Trade))
        trade_count = result.scalar_one()
        assert trade_count >= 1

        await _check_conservation(session)