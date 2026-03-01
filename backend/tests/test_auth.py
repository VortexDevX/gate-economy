import uuid

import pytest
from httpx import AsyncClient


def _unique() -> tuple[str, str]:
    """Generate a unique username and email for each test."""
    tag = uuid.uuid4().hex[:8]
    return f"user_{tag}", f"user_{tag}@test.com"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    username, email = _unique()
    resp = await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == username
    assert data["balance_micro"] == 10_000_000


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    username, email = _unique()
    resp1 = await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    assert resp1.status_code == 201

    _, email2 = _unique()
    resp2 = await client.post("/auth/register", json={
        "username": username,
        "email": email2,
        "password": "securepass123",
    })
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    username, email = _unique()
    resp1 = await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    assert resp1.status_code == 201

    username2, _ = _unique()
    resp2 = await client.post("/auth/register", json={
        "username": username2,
        "email": email,
        "password": "securepass123",
    })
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    username, email = _unique()
    resp = await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "short",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    username, email = _unique()
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })

    resp = await client.post("/auth/login", json={
        "email": email,
        "password": "securepass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    username, email = _unique()
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })

    resp = await client.post("/auth/login", json={
        "email": email,
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "securepass123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/players/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/players/me",
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile(client: AsyncClient):
    username, email = _unique()
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    login_resp = await client.post("/auth/login", json={
        "email": email,
        "password": "securepass123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/players/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == username
    assert data["balance_micro"] == 10_000_000


@pytest.mark.asyncio
async def test_my_ledger(client: AsyncClient):
    username, email = _unique()
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    login_resp = await client.post("/auth/login", json={
        "email": email,
        "password": "securepass123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/players/me/ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["entry_type"] == "STARTING_GRANT"
    assert data["items"][0]["amount_micro"] == 10_000_000


@pytest.mark.asyncio
async def test_refresh_flow(client: AsyncClient):
    username, email = _unique()
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "securepass123",
    })
    login_resp = await client.post("/auth/login", json={
        "email": email,
        "password": "securepass123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    # New access token works
    me_resp = await client.get(
        "/players/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200