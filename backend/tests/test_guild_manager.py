"""Guild manager simulation-level tests."""

import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import and_, func, select

from app.config import settings
from app.models.gate import DiscoveryType, Gate, GateRank, GateShare, GateStatus
from app.models.guild import Guild, GuildGateHolding, GuildMember, GuildRole, GuildShare, GuildStatus
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.ledger import AccountEntityType, EntryType
from app.models.market import AssetType, Order, OrderSide, OrderStatus
from app.models.player import Player
from app.models.treasury import AccountType, SystemAccount
from app.services.order_matching import calculate_iso_price
from app.services.transfer import transfer
from app.simulation.tick import execute_tick
from app.models.gate import GateRankProfile


@pytest.fixture(autouse=True)
def _stable_world():
    """Disable random gate spawns so guild tests remain deterministic."""
    original = settings.system_spawn_probability
    settings.system_spawn_probability = 0.0
    yield
    settings.system_spawn_probability = original


@contextmanager
def _settings(**overrides):
    """Temporarily override settings used by tick pipeline logic."""
    old = {}
    for k, v in overrides.items():
        old[k] = getattr(settings, k)
        setattr(settings, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(settings, k, v)


async def _treasury_id(sf) -> uuid.UUID:
    async with sf() as session:
        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        return result.scalar_one()


async def _create_player_with_balance(sf, amount_micro: int) -> uuid.UUID:
    """Create a player and fund it from treasury, preserving conservation."""
    async with sf() as session:
        player_id = uuid.uuid4()
        player = Player(
            id=player_id,
            username=f"guild_{uuid.uuid4().hex[:8]}",
            email=f"guild_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="not-a-real-hash",
            balance_micro=0,
        )
        session.add(player)
        await session.flush()

        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id = result.scalar_one()
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM,
            from_id=treasury_id,
            to_type=AccountEntityType.PLAYER,
            to_id=player_id,
            amount=amount_micro,
            entry_type=EntryType.STARTING_GRANT,
            memo="test funding",
        )
        await session.commit()
        return player_id


async def _balance(sf, player_id: uuid.UUID) -> int:
    async with sf() as session:
        result = await session.execute(
            select(Player.balance_micro).where(Player.id == player_id)
        )
        return result.scalar_one()


async def _queue_intent(sf, player_id: uuid.UUID, intent_type: IntentType, payload: dict) -> uuid.UUID:
    async with sf() as session:
        intent = Intent(
            player_id=player_id,
            intent_type=intent_type,
            payload=payload,
            status=IntentStatus.QUEUED,
        )
        session.add(intent)
        await session.commit()
        return intent.id


async def _get_intent(sf, intent_id: uuid.UUID) -> Intent:
    async with sf() as session:
        result = await session.execute(select(Intent).where(Intent.id == intent_id))
        return result.scalar_one()


async def _create_active_gate(sf, total_shares: int = 100, base_yield_micro: int = 10_000) -> uuid.UUID:
    async with sf() as session:
        gate = Gate(
            rank=GateRank.E,
            stability=100.0,
            volatility=0.0,
            base_yield_micro=base_yield_micro,
            total_shares=total_shares,
            status=GateStatus.ACTIVE,
            spawned_at_tick=1,
            discovery_type=DiscoveryType.SYSTEM,
        )
        session.add(gate)
        await session.commit()
        return gate.id


async def _fund_guild(sf, guild_id: uuid.UUID, amount_micro: int):
    async with sf() as session:
        result = await session.execute(
            select(SystemAccount.id).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury_id = result.scalar_one()
        await transfer(
            session=session,
            from_type=AccountEntityType.SYSTEM,
            from_id=treasury_id,
            to_type=AccountEntityType.GUILD,
            to_id=guild_id,
            amount=amount_micro,
            entry_type=EntryType.ADMIN_ADJUSTMENT,
            memo="test guild funding",
        )
        await session.commit()


@pytest.mark.asyncio
async def test_create_guild_success_deducts_fee_and_sets_shares(session_factory, pause_simulation):
    founder_id = await _create_player_with_balance(session_factory, 120_000_000)
    before = await _balance(session_factory, founder_id)

    intent_id = await _queue_intent(
        session_factory,
        founder_id,
        IntentType.CREATE_GUILD,
        {
            "name": "Alpha",
            "public_float_pct": 0.30,
            "dividend_policy": "MANUAL",
        },
    )
    await execute_tick(session_factory)
    intent = await _get_intent(session_factory, intent_id)
    assert intent.status == IntentStatus.EXECUTED

    async with session_factory() as session:
        result = await session.execute(select(Guild).where(Guild.name == "Alpha"))
        guild = result.scalar_one()
        result = await session.execute(
            select(GuildMember.role).where(
                GuildMember.guild_id == guild.id,
                GuildMember.player_id == founder_id,
            )
        )
        assert result.scalar_one() == GuildRole.LEADER
        result = await session.execute(
            select(GuildShare.quantity).where(
                GuildShare.guild_id == guild.id,
                GuildShare.player_id == founder_id,
            )
        )
        founder_qty = result.scalar_one()
        result = await session.execute(
            select(GuildShare.quantity).where(
                GuildShare.guild_id == guild.id,
                GuildShare.player_id == guild.id,
            )
        )
        float_qty = result.scalar_one()

    assert founder_qty == 700
    assert float_qty == 300
    assert await _balance(session_factory, founder_id) == before - settings.guild_creation_cost_micro


@pytest.mark.asyncio
async def test_create_guild_duplicate_name_rejected(session_factory, pause_simulation):
    p1 = await _create_player_with_balance(session_factory, 120_000_000)
    p2 = await _create_player_with_balance(session_factory, 120_000_000)
    await _queue_intent(
        session_factory,
        p1,
        IntentType.CREATE_GUILD,
        {"name": "Dup", "public_float_pct": 0.2, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)

    i2 = await _queue_intent(
        session_factory,
        p2,
        IntentType.CREATE_GUILD,
        {"name": "Dup", "public_float_pct": 0.2, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)
    intent = await _get_intent(session_factory, i2)
    assert intent.status == IntentStatus.REJECTED
    assert "already taken" in (intent.reject_reason or "")


@pytest.mark.asyncio
async def test_create_guild_insufficient_balance_rejected(
    session_factory, pause_simulation, funded_player_id
):
    intent_id = await _queue_intent(
        session_factory,
        funded_player_id,
        IntentType.CREATE_GUILD,
        {"name": "Poor", "public_float_pct": 0.2, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)
    intent = await _get_intent(session_factory, intent_id)
    assert intent.status == IntentStatus.REJECTED
    assert "Insufficient balance" in (intent.reject_reason or "")


@pytest.mark.asyncio
async def test_guild_iso_order_created(session_factory, pause_simulation):
    founder_id = await _create_player_with_balance(session_factory, 120_000_000)
    await _queue_intent(
        session_factory,
        founder_id,
        IntentType.CREATE_GUILD,
        {"name": "IsoGuild", "public_float_pct": 0.30, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(select(Guild).where(Guild.name == "IsoGuild"))
        guild = result.scalar_one()
        result = await session.execute(
            select(Order).where(
                and_(
                    Order.asset_type == AssetType.GUILD_SHARE,
                    Order.asset_id == guild.id,
                    Order.side == OrderSide.SELL,
                    Order.status == OrderStatus.OPEN,
                    Order.guild_id == guild.id,
                )
            )
        )
        order = result.scalar_one()
        assert order.quantity == 300
        assert order.price_limit_micro == settings.guild_creation_cost_micro // settings.guild_total_shares


@pytest.mark.asyncio
async def test_manual_dividend_distributes_to_leader(session_factory, pause_simulation):
    with _settings(guild_base_maintenance_micro=1, guild_maintenance_scale=0.0):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {"name": "DivGuild", "public_float_pct": 0.0, "dividend_policy": "MANUAL"},
        )
        await execute_tick(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "DivGuild"))
            guild = result.scalar_one()
            guild_id = guild.id

        await _fund_guild(session_factory, guild_id, 200_000)
        before = await _balance(session_factory, founder_id)

        intent_id = await _queue_intent(
            session_factory,
            founder_id,
            IntentType.GUILD_DIVIDEND,
            {"guild_id": str(guild_id), "amount_micro": 100_000},
        )
        await execute_tick(session_factory)
        intent = await _get_intent(session_factory, intent_id)
        assert intent.status == IntentStatus.EXECUTED
        assert await _balance(session_factory, founder_id) == before + 100_000


@pytest.mark.asyncio
async def test_manual_dividend_non_leader_rejected(session_factory, pause_simulation):
    founder_id = await _create_player_with_balance(session_factory, 120_000_000)
    other_id = await _create_player_with_balance(session_factory, 120_000_000)
    await _queue_intent(
        session_factory,
        founder_id,
        IntentType.CREATE_GUILD,
        {"name": "NoDiv", "public_float_pct": 0.0, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(select(Guild).where(Guild.name == "NoDiv"))
        guild_id = result.scalar_one().id
    await _fund_guild(session_factory, guild_id, 100_000)

    intent_id = await _queue_intent(
        session_factory,
        other_id,
        IntentType.GUILD_DIVIDEND,
        {"guild_id": str(guild_id), "amount_micro": 50_000},
    )
    await execute_tick(session_factory)
    intent = await _get_intent(session_factory, intent_id)
    assert intent.status == IntentStatus.REJECTED
    assert "Only the guild leader" in (intent.reject_reason or "")


@pytest.mark.asyncio
async def test_auto_dividend_runs_each_tick(session_factory, pause_simulation):
    with _settings(guild_base_maintenance_micro=1, guild_maintenance_scale=0.0):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {
                "name": "AutoDiv",
                "public_float_pct": 0.0,
                "dividend_policy": "AUTO_FIXED_PCT",
                "auto_dividend_pct": 0.10,
            },
        )
        await execute_tick(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "AutoDiv"))
            guild_id = result.scalar_one().id
        await _fund_guild(session_factory, guild_id, 100_000)
        before = await _balance(session_factory, founder_id)

        await execute_tick(session_factory)
        # 100_000 funded, then maintenance 1, then 10% auto dividend of 99_999 => 9_999
        assert await _balance(session_factory, founder_id) == before + 9_999


@pytest.mark.asyncio
async def test_guild_invest_matches_gate_iso_and_receives_holdings(
    session_factory, pause_simulation
):
    with _settings(guild_base_maintenance_micro=1, guild_maintenance_scale=0.0):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        treasury_id = await _treasury_id(session_factory)

        async with session_factory() as session:
            gate = Gate(
                rank=GateRank.E,
                stability=100.0,
                volatility=0.0,
                base_yield_micro=3_000,
                total_shares=100,
                status=GateStatus.OFFERING,
                spawned_at_tick=1,
                discovery_type=DiscoveryType.SYSTEM,
            )
            session.add(gate)
            await session.flush()
            session.add(GateShare(gate_id=gate.id, player_id=treasury_id, quantity=100))
            gate_id = gate.id
            await session.commit()

        await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {"name": "InvestGuild", "public_float_pct": 0.0, "dividend_policy": "MANUAL"},
        )
        await execute_tick(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "InvestGuild"))
            guild_id = result.scalar_one().id

        await _fund_guild(session_factory, guild_id, 500_000)

        async with session_factory() as session:
            result = await session.execute(
                select(GateRankProfile).where(GateRankProfile.rank == GateRank.E)
            )
            profile = result.scalar_one()
        iso_price = calculate_iso_price(profile)

        intent_id = await _queue_intent(
            session_factory,
            founder_id,
            IntentType.GUILD_INVEST,
            {
                "guild_id": str(guild_id),
                "gate_id": str(gate_id),
                "quantity": 10,
                "price_limit_micro": iso_price,
            },
        )
        await execute_tick(session_factory)
        intent = await _get_intent(session_factory, intent_id)
        assert intent.status == IntentStatus.EXECUTED

        async with session_factory() as session:
            result = await session.execute(
                select(GuildGateHolding.quantity).where(
                    and_(
                        GuildGateHolding.guild_id == guild_id,
                        GuildGateHolding.gate_id == gate_id,
                    )
                )
            )
            assert result.scalar_one() == 10


@pytest.mark.asyncio
async def test_guild_receives_yield_from_gate_holdings(session_factory, pause_simulation):
    with _settings(guild_base_maintenance_micro=1, guild_maintenance_scale=0.0):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        gate_id = await _create_active_gate(session_factory, total_shares=100, base_yield_micro=10_000)

        await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {"name": "YieldGuild", "public_float_pct": 0.0, "dividend_policy": "MANUAL"},
        )
        await execute_tick(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "YieldGuild"))
            guild = result.scalar_one()
            session.add(GuildGateHolding(guild_id=guild.id, gate_id=gate_id, quantity=100))
            await session.commit()
            guild_id = guild.id

        await execute_tick(session_factory)
        async with session_factory() as session:
            result = await session.execute(select(Guild.treasury_micro).where(Guild.id == guild_id))
            # Gate already decayed once on tick 1 before holdings existed.
            # Tick 2 yield uses stability 99.8% => 9_980, minus maintenance 1.
            assert result.scalar_one() == 9_979


@pytest.mark.asyncio
async def test_insolvent_guild_gets_yield_penalty(session_factory, pause_simulation):
    with _settings(guild_base_maintenance_micro=1, guild_maintenance_scale=0.0):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        gate_id = await _create_active_gate(session_factory, total_shares=100, base_yield_micro=10_000)

        await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {"name": "InsolventYield", "public_float_pct": 0.0, "dividend_policy": "MANUAL"},
        )
        await execute_tick(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "InsolventYield"))
            guild = result.scalar_one()
            guild.status = GuildStatus.INSOLVENT
            guild.insolvent_ticks = 0
            session.add(GuildGateHolding(guild_id=guild.id, gate_id=gate_id, quantity=100))
            await session.commit()
            guild_id = guild.id

        await execute_tick(session_factory)
        async with session_factory() as session:
            result = await session.execute(select(Guild.treasury_micro, Guild.status).where(Guild.id == guild_id))
            treasury_micro, status = result.one()
            # Gate already decayed once on tick 1 before holdings existed.
            # Tick 2 payout base is 9_980, insolvent gets 50% => 4_990, then maintenance 1.
            assert treasury_micro == 4_989
            assert status == GuildStatus.ACTIVE


@pytest.mark.asyncio
async def test_insolvency_and_dissolution_cancel_open_orders(
    session_factory, pause_simulation, funded_player_id
):
    with _settings(
        guild_insolvency_threshold=2,
        guild_dissolution_threshold=3,
        guild_base_maintenance_micro=100_000,
        guild_maintenance_scale=0.0,
    ):
        founder_id = await _create_player_with_balance(session_factory, 120_000_000)
        create_intent = await _queue_intent(
            session_factory,
            founder_id,
            IntentType.CREATE_GUILD,
            {"name": "DecayGuild", "public_float_pct": 0.30, "dividend_policy": "MANUAL"},
        )
        await execute_tick(session_factory)  # tick 1 (missed=1)
        assert (await _get_intent(session_factory, create_intent)).status == IntentStatus.EXECUTED

        async with session_factory() as session:
            result = await session.execute(select(Guild).where(Guild.name == "DecayGuild"))
            guild_id = result.scalar_one().id

        buyer_before = await _balance(session_factory, funded_player_id)
        buy_intent = await _queue_intent(
            session_factory,
            funded_player_id,
            IntentType.PLACE_ORDER,
            {
                "asset_type": "GUILD_SHARE",
                "asset_id": str(guild_id),
                "side": "BUY",
                "quantity": 5,
                "price_limit_micro": 1_000,
            },
        )
        await execute_tick(session_factory)  # tick 2 -> guild insolvent, order open
        assert (await _get_intent(session_factory, buy_intent)).status == IntentStatus.EXECUTED

        await execute_tick(session_factory)  # tick 3
        await execute_tick(session_factory)  # tick 4 -> dissolution expected

        async with session_factory() as session:
            result = await session.execute(select(Guild.status).where(Guild.id == guild_id))
            assert result.scalar_one() == GuildStatus.DISSOLVED
            result = await session.execute(
                select(Order.status).where(
                    and_(
                        Order.asset_type == AssetType.GUILD_SHARE,
                        Order.asset_id == guild_id,
                        Order.side == OrderSide.BUY,
                        Order.player_id == funded_player_id,
                    )
                )
            )
            assert result.scalar_one() == OrderStatus.CANCELLED
        assert await _balance(session_factory, funded_player_id) == buyer_before


@pytest.mark.asyncio
async def test_conservation_after_guild_operations(session_factory, pause_simulation):
    founder_id = await _create_player_with_balance(session_factory, 120_000_000)
    await _queue_intent(
        session_factory,
        founder_id,
        IntentType.CREATE_GUILD,
        {"name": "ConserveGuild", "public_float_pct": 0.20, "dividend_policy": "MANUAL"},
    )
    await execute_tick(session_factory)

    async with session_factory() as session:
        result = await session.execute(
            select(SystemAccount.balance_micro).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury = int(result.scalar_one())
        result = await session.execute(select(func.coalesce(func.sum(Player.balance_micro), 0)))
        players = int(result.scalar_one())
        result = await session.execute(select(func.coalesce(func.sum(Guild.treasury_micro), 0)))
        guilds = int(result.scalar_one())

    assert treasury + players + guilds == settings.initial_seed_micro
