from typing import Any, cast

from redis.asyncio import Redis

# Lua script: delete key only if value matches (atomic compare-and-delete)
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

_REFRESH_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""

LOCK_KEY = "sim:leader"
LOCK_TTL_SECONDS = 30


class SimulationLock:
    """Redis-based leadership lock for the simulation worker.

    Ensures only one worker can execute a tick at any given time.
    TTL acts as a safety net — if a worker crashes mid-tick,
    the lock expires and another worker can take over.
    """

    def __init__(
        self, redis: Redis, worker_id: str, lock_key: str = LOCK_KEY
    ) -> None:
        self._redis = redis
        self._worker_id = worker_id
        self._lock_key = lock_key

    async def acquire(self) -> bool:
        """Attempt to acquire the leadership lock.

        Returns True if acquired, False if another worker holds it.
        """
        result = await self._redis.set(
            self._lock_key,
            self._worker_id,
            nx=True,
            ex=LOCK_TTL_SECONDS,
        )
        return result is not None

    async def release(self) -> bool:
        """Release the lock only if we still hold it.

        Returns True if released, False if lock was already gone
        or held by another worker (e.g., after TTL expiry).
        """
        result = cast(Any, await self._redis.eval(
            _RELEASE_SCRIPT,
            1,
            self._lock_key,  # type: ignore
            self._worker_id,  # type: ignore
        ))
        return bool(result == 1)

    async def refresh(self) -> bool:
        """Extend the lock TTL only if this worker still owns it."""
        result = cast(Any, await self._redis.eval(
            _REFRESH_SCRIPT,
            1,
            self._lock_key,  # type: ignore
            self._worker_id,  # type: ignore
            LOCK_TTL_SECONDS,
        ))
        return bool(result == 1)
