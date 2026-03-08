import pytest
import pytest_asyncio
from sqlalchemy import select

from app.config import settings
from app.models.player import Player, PlayerRole
from app.services.admin import PAUSE_KEY


# ── Local fixtures ──


@pytest_asyncio.fixture(autouse=True)
async def _clean_pause_flag():
    """Ensure pause flag is cleared after every test."""
    yield
    from redis.asyncio import Redis as R
    r = R.from_url(settings.redis_url, decode_responses=True)
    await r.delete(PAUSE_KEY)
    await r.aclose()


@pytest_asyncio.fixture
async def admin_headers(client, session_factory):
    """Register → promote to ADMIN → login → return auth headers."""
    resp = await client.post("/auth/register", json={
        "username": "admin_tester",
        "email": "admin_tester@test.com",
        "password": "AdminPass123!",
    })
    assert resp.status_code == 201

    async with session_factory() as session:
        result = await session.execute(
            select(Player).where(Player.username == "admin_tester")
        )
        player = result.scalar_one()
        player.role = PlayerRole.ADMIN
        await session.commit()

    resp = await client.post("/auth/login", json={
        "email": "admin_tester@test.com",
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def player_headers(client):
    """Register a regular player → login → return auth headers."""
    resp = await client.post("/auth/register", json={
        "username": "regular_player",
        "email": "regular@test.com",
        "password": "PlayerPass123!",
    })
    assert resp.status_code == 201
    resp = await client.post("/auth/login", json={
        "email": "regular@test.com",
        "password": "PlayerPass123!",
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def seeded_params(session_factory):
    """Seed simulation parameters from current settings."""
    async with session_factory() as session:
        from app.services.admin import seed_parameters
        await seed_parameters(session)
        await session.commit()


# ── Auth / Authorization ──


@pytest.mark.asyncio
async def test_non_admin_blocked(client, player_headers):
    resp = await client.post("/admin/simulation/pause", headers=player_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_blocked(client):
    resp = await client.post("/admin/simulation/pause")
    assert resp.status_code in (401, 403)


# ── Simulation Pause / Resume ──


@pytest.mark.asyncio
async def test_pause_simulation(client, admin_headers):
    resp = await client.post("/admin/simulation/pause", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_simulation(client, admin_headers):
    # Set pause via API first
    resp = await client.post("/admin/simulation/pause", headers=admin_headers)
    assert resp.status_code == 200
    resp = await client.post("/admin/simulation/resume", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


# ── Parameters ──


@pytest.mark.asyncio
async def test_list_parameters(client, admin_headers, seeded_params):
    resp = await client.get("/admin/parameters", headers=admin_headers)
    assert resp.status_code == 200
    params = resp.json()
    assert len(params) > 0
    keys = {p["key"] for p in params}
    assert "event_probability" in keys
    assert "system_spawn_probability" in keys


@pytest.mark.asyncio
async def test_update_parameter_success(client, admin_headers, seeded_params):
    orig = settings.event_probability
    try:
        resp = await client.patch(
            "/admin/parameters/event_probability",
            json={"value": "0.25"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "event_probability"
        assert data["value"] == "0.25"
    finally:
        settings.event_probability = orig


@pytest.mark.asyncio
async def test_update_parameter_invalid_key(client, admin_headers, seeded_params):
    resp = await client.patch(
        "/admin/parameters/nonexistent_key",
        json={"value": "123"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Unknown parameter" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_parameter_invalid_value(client, admin_headers, seeded_params):
    resp = await client.patch(
        "/admin/parameters/gate_offering_ticks",
        json={"value": "not_a_number"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


# ── Conservation Audit ──


@pytest.mark.asyncio
async def test_conservation_audit_pass(client, admin_headers):
    resp = await client.get("/admin/audit/conservation", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PASS"
    assert data["delta_micro"] == 0


@pytest.mark.asyncio
async def test_conservation_audit_fail(client, admin_headers, session_factory):
    async with session_factory() as session:
        result = await session.execute(
            select(Player).where(Player.username == "admin_tester")
        )
        player = result.scalar_one()
        player.balance_micro += 1_000_000
        await session.commit()

    resp = await client.get("/admin/audit/conservation", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAIL"
    assert data["delta_micro"] == 1_000_000


# ── Treasury & Ledger ──


@pytest.mark.asyncio
async def test_treasury_view(client, admin_headers):
    resp = await client.get("/admin/treasury", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "treasury_id" in data
    assert "balance_micro" in data
    assert isinstance(data["recent_entries"], list)


@pytest.mark.asyncio
async def test_ledger_view(client, admin_headers):
    resp = await client.get("/admin/ledger", headers=admin_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)
    # admin registration created a STARTING_GRANT entry
    assert len(entries) >= 1


@pytest.mark.asyncio
async def test_ledger_filter_entry_type(client, admin_headers):
    resp = await client.get(
        "/admin/ledger?entry_type=STARTING_GRANT", headers=admin_headers
    )
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["entry_type"] == "STARTING_GRANT"


@pytest.mark.asyncio
async def test_ledger_filter_invalid_type(client, admin_headers):
    resp = await client.get(
        "/admin/ledger?entry_type=BOGUS_TYPE", headers=admin_headers
    )
    assert resp.status_code == 400


# ── Events ──


@pytest.mark.asyncio
async def test_trigger_event(client, admin_headers):
    resp = await client.post(
        "/admin/events/trigger",
        json={"event_type": "STABILITY_SURGE"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "STABILITY_SURGE"
    assert "event_id" in data


@pytest.mark.asyncio
async def test_trigger_event_invalid_type(client, admin_headers):
    resp = await client.post(
        "/admin/events/trigger",
        json={"event_type": "NONEXISTENT"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


# ── Seasons ──


@pytest.mark.asyncio
async def test_season_create(client, admin_headers):
    resp = await client.post(
        "/admin/seasons", json={"action": "create"}, headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "create"
    assert data["season_number"] == 1


@pytest.mark.asyncio
async def test_season_create_conflict(client, admin_headers):
    resp = await client.post(
        "/admin/seasons", json={"action": "create"}, headers=admin_headers
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/admin/seasons", json={"action": "create"}, headers=admin_headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_season_end_no_active(client, admin_headers):
    resp = await client.post(
        "/admin/seasons", json={"action": "end"}, headers=admin_headers
    )
    assert resp.status_code == 404


# ── Metrics ──


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "dge_tick_number" in body
    assert "dge_tick_duration_seconds" in body
    assert "dge_intent_queue_depth" in body
    assert "dge_active_players_total" in body
    assert "dge_treasury_balance_micro" in body
    assert "dge_trade_volume_micro" in body
    assert "dge_active_gates_total" in body
    assert "dge_ws_connections" in body
    assert "dge_order_book_depth" in body
    assert "dge_events_fired_total" in body