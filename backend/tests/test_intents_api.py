import uuid

import pytest


async def _register_and_login(client) -> dict:
    """Register a unique user and return auth headers."""
    unique = uuid.uuid4().hex[:8]
    await client.post(
        "/auth/register",
        json={
            "username": f"intent_{unique}",
            "email": f"intent_{unique}@test.com",
            "password": "SecurePass123!",
        },
    )
    login_resp = await client.post(
        "/auth/login",
        json={
            "email": f"intent_{unique}@test.com",
            "password": "SecurePass123!",
        },
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_submit_intent_returns_queued(client):
    """Authenticated intent submission returns 201 with QUEUED status."""
    headers = await _register_and_login(client)

    resp = await client.post(
        "/intents",
        json={
            "intent_type": "DISCOVER_GATE",
            "payload": {"min_rank": "C"},
        },
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "QUEUED"
    assert body["intent_type"] == "DISCOVER_GATE"
    assert "id" in body
    assert body["processed_tick"] is None


@pytest.mark.asyncio
async def test_submit_intent_all_types_accepted(client):
    """All valid intent types are accepted as QUEUED."""
    headers = await _register_and_login(client)
    valid_payloads = {
        "DISCOVER_GATE": {"min_rank": "E"},
        "PLACE_ORDER": {
            "asset_type": "GATE_SHARE",
            "asset_id": str(uuid.uuid4()),
            "side": "BUY",
            "quantity": 1,
            "price_limit_micro": 1,
        },
        "CANCEL_ORDER": {"order_id": str(uuid.uuid4())},
        "CREATE_GUILD": {
            "name": f"Guild-{uuid.uuid4().hex[:8]}",
            "public_float_pct": 0.2,
            "dividend_policy": "MANUAL",
        },
        "GUILD_DIVIDEND": {"guild_id": str(uuid.uuid4())},
        "GUILD_INVEST": {
            "guild_id": str(uuid.uuid4()),
            "gate_id": str(uuid.uuid4()),
            "quantity": 1,
            "price_limit_micro": 1,
        },
    }

    for intent_type, payload in valid_payloads.items():
        resp = await client.post(
            "/intents",
            json={"intent_type": intent_type, "payload": payload},
            headers=headers,
        )
        assert resp.status_code == 201, f"Failed for {intent_type}"
        assert resp.json()["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_submit_intent_empty_payload_rejected_for_all_types(client):
    """Every current intent requires at least one type-specific payload field."""
    headers = await _register_and_login(client)

    for intent_type in (
        "DISCOVER_GATE",
        "PLACE_ORDER",
        "CANCEL_ORDER",
        "CREATE_GUILD",
        "GUILD_DIVIDEND",
        "GUILD_INVEST",
    ):
        resp = await client.post(
            "/intents",
            json={"intent_type": intent_type, "payload": {}},
            headers=headers,
        )
        assert resp.status_code == 422, f"Accepted empty payload for {intent_type}"

    queued = await client.get("/intents/me", headers=headers)
    assert queued.status_code == 200
    assert queued.json()["total"] == 0


@pytest.mark.asyncio
async def test_submit_intent_invalid_typed_payloads_rejected(client):
    """Malformed type-specific values never enter the intent queue."""
    headers = await _register_and_login(client)
    invalid_requests = (
        {"intent_type": "DISCOVER_GATE", "payload": {"min_rank": "X"}},
        {
            "intent_type": "CANCEL_ORDER",
            "payload": {"order_id": "not-a-uuid"},
        },
        {
            "intent_type": "CREATE_GUILD",
            "payload": {
                "name": "   ",
                "public_float_pct": 0.2,
                "dividend_policy": "MANUAL",
            },
        },
        {
            "intent_type": "GUILD_DIVIDEND",
            "payload": {
                "guild_id": str(uuid.uuid4()),
                "amount_micro": "many",
            },
        },
        {
            "intent_type": "GUILD_INVEST",
            "payload": {
                "guild_id": str(uuid.uuid4()),
                "gate_id": "not-a-uuid",
                "quantity": 1,
                "price_limit_micro": 1,
            },
        },
    )

    for request in invalid_requests:
        resp = await client.post("/intents", json=request, headers=headers)
        assert resp.status_code == 422, f"Accepted malformed request: {request}"

    queued = await client.get("/intents/me", headers=headers)
    assert queued.status_code == 200
    assert queued.json()["total"] == 0


@pytest.mark.asyncio
async def test_submit_place_order_null_quantity_rejected(client):
    """Regression: null quantity must fail at API boundary, not during a tick."""
    headers = await _register_and_login(client)

    resp = await client.post(
        "/intents",
        json={
            "intent_type": "PLACE_ORDER",
            "payload": {
                "asset_type": "GATE_SHARE",
                "asset_id": str(uuid.uuid4()),
                "side": "BUY",
                "quantity": None,
                "price_limit_micro": 1,
            },
        },
        headers=headers,
    )

    assert resp.status_code == 422
    queued = await client.get("/intents/me", headers=headers)
    assert queued.status_code == 200
    assert queued.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_guild_auto_dividend_rules_validated(client):
    headers = await _register_and_login(client)

    valid = await client.post(
        "/intents",
        json={
            "intent_type": "CREATE_GUILD",
            "payload": {
                "name": f"Auto-{uuid.uuid4().hex[:8]}",
                "public_float_pct": 0.2,
                "dividend_policy": "AUTO_FIXED_PCT",
                "auto_dividend_pct": 0.1,
            },
        },
        headers=headers,
    )
    missing_rate = await client.post(
        "/intents",
        json={
            "intent_type": "CREATE_GUILD",
            "payload": {
                "name": f"Missing-{uuid.uuid4().hex[:8]}",
                "public_float_pct": 0.2,
                "dividend_policy": "AUTO_FIXED_PCT",
            },
        },
        headers=headers,
    )
    manual_with_rate = await client.post(
        "/intents",
        json={
            "intent_type": "CREATE_GUILD",
            "payload": {
                "name": f"Manual-{uuid.uuid4().hex[:8]}",
                "public_float_pct": 0.2,
                "dividend_policy": "MANUAL",
                "auto_dividend_pct": 0.1,
            },
        },
        headers=headers,
    )

    assert valid.status_code == 201
    assert missing_rate.status_code == 422
    assert manual_with_rate.status_code == 422


@pytest.mark.asyncio
async def test_submit_intent_no_auth_rejected(client):
    """Intent submission without auth returns 401 or 403."""
    resp = await client.post(
        "/intents",
        json={
            "intent_type": "DISCOVER_GATE",
            "payload": {"min_rank": "E"},
        },
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_submit_intent_invalid_type_rejected(client):
    """Invalid intent type returns 422 validation error."""
    headers = await _register_and_login(client)

    resp = await client.post(
        "/intents",
        json={"intent_type": "INVALID_TYPE", "payload": {}},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_intent_missing_payload_rejected(client):
    """Missing payload field returns 422."""
    headers = await _register_and_login(client)

    resp = await client.post(
        "/intents",
        json={"intent_type": "DISCOVER_GATE"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_my_intents_returns_recent(client):
    headers = await _register_and_login(client)

    await client.post(
        "/intents",
        json={"intent_type": "DISCOVER_GATE", "payload": {"min_rank": "E"}},
        headers=headers,
    )
    await client.post(
        "/intents",
        json={
            "intent_type": "PLACE_ORDER",
            "payload": {
                "asset_type": "GATE_SHARE",
                "asset_id": str(uuid.uuid4()),
                "side": "BUY",
                "quantity": 1,
                "price_limit_micro": 1,
            },
        },
        headers=headers,
    )

    resp = await client.get("/intents/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2
    assert body["items"][0]["intent_type"] in (
        "DISCOVER_GATE",
        "PLACE_ORDER",
    )
