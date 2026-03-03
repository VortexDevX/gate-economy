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
    valid_types = [
        "DISCOVER_GATE",
        "PLACE_ORDER",
        "CANCEL_ORDER",
        "CREATE_GUILD",
        "GUILD_DIVIDEND",
        "GUILD_INVEST",
    ]

    for intent_type in valid_types:
        resp = await client.post(
            "/intents",
            json={"intent_type": intent_type, "payload": {}},
            headers=headers,
        )
        assert resp.status_code == 201, f"Failed for {intent_type}"
        assert resp.json()["status"] == "QUEUED"


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