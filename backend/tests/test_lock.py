import uuid

import pytest

from app.simulation.lock import SimulationLock


@pytest.mark.asyncio
async def test_acquire_succeeds(redis_client):
    """First acquire on a free lock succeeds."""
    lock_key = f"sim:leader:test:{uuid.uuid4().hex}"
    await redis_client.delete(lock_key)
    lock = SimulationLock(redis_client, "worker-1", lock_key=lock_key)

    assert await lock.acquire() is True
    await lock.release()


@pytest.mark.asyncio
async def test_double_acquire_fails(redis_client):
    """Second worker cannot acquire while first holds the lock."""
    lock_key = f"sim:leader:test:{uuid.uuid4().hex}"
    await redis_client.delete(lock_key)
    lock_1 = SimulationLock(redis_client, "worker-1", lock_key=lock_key)
    lock_2 = SimulationLock(redis_client, "worker-2", lock_key=lock_key)

    assert await lock_1.acquire() is True
    assert await lock_2.acquire() is False

    await lock_1.release()


@pytest.mark.asyncio
async def test_release_and_reacquire(redis_client):
    """After release, another worker can acquire."""
    lock_key = f"sim:leader:test:{uuid.uuid4().hex}"
    await redis_client.delete(lock_key)
    lock_1 = SimulationLock(redis_client, "worker-1", lock_key=lock_key)
    lock_2 = SimulationLock(redis_client, "worker-2", lock_key=lock_key)

    assert await lock_1.acquire() is True
    assert await lock_1.release() is True
    assert await lock_2.acquire() is True

    await lock_2.release()


@pytest.mark.asyncio
async def test_release_wrong_worker_is_noop(redis_client):
    """A worker cannot release another worker's lock."""
    lock_key = f"sim:leader:test:{uuid.uuid4().hex}"
    await redis_client.delete(lock_key)
    lock_1 = SimulationLock(redis_client, "worker-1", lock_key=lock_key)
    lock_2 = SimulationLock(redis_client, "worker-2", lock_key=lock_key)

    assert await lock_1.acquire() is True
    # worker-2 tries to release worker-1's lock → fails
    assert await lock_2.release() is False
    # lock is still held by worker-1
    assert await lock_2.acquire() is False
    # worker-1 can still release
    assert await lock_1.release() is True


@pytest.mark.asyncio
async def test_release_already_expired_is_safe(redis_client):
    """Releasing a lock that no longer exists returns False, no error."""
    lock_key = f"sim:leader:test:{uuid.uuid4().hex}"
    await redis_client.delete(lock_key)
    lock = SimulationLock(redis_client, "worker-1", lock_key=lock_key)

    # Nothing to release
    assert await lock.release() is False
