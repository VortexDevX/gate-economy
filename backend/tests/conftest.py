import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired directly to the ASGI app (no network)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
