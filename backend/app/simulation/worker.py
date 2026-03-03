import asyncio
import logging
import os
import socket
import uuid

import structlog
from celery import Celery
from celery.signals import worker_init
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.simulation.lock import SimulationLock
from app.simulation.tick import execute_tick

# ── Celery app ──

celery_app = Celery(
    "simulation",
    broker=settings.celery_broker_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "simulation-tick": {
            "task": "app.simulation.worker.run_tick",
            "schedule": float(settings.simulation_tick_interval),
        },
    },
)

# Unique worker ID: hostname + PID + random suffix
_worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


# ── Logging setup for Celery process ──


@worker_init.connect
def _setup_worker_logging(**kwargs):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ── Helpers ──

logger = structlog.get_logger()


def _make_session_factory():
    """Create a fresh engine + session factory for one tick.

    Uses NullPool because asyncio.run() creates a new event loop
    per invocation — persistent connection pools would bind to
    the wrong loop on subsequent calls.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    return factory, engine


# ── Task ──


@celery_app.task(name="app.simulation.worker.run_tick", max_retries=0)
def run_tick():
    """Celery task entry point. Bridges sync Celery → async tick pipeline."""
    asyncio.run(_run_tick_async())


async def _run_tick_async():
    """Acquire lock, execute tick, release lock. All async."""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    lock = SimulationLock(redis, _worker_id)
    acquired = False

    try:
        acquired = await lock.acquire()
        if not acquired:
            logger.debug("tick_skipped_lock_held", worker_id=_worker_id)
            return

        factory, engine = _make_session_factory()
        try:
            await execute_tick(factory)
        finally:
            await engine.dispose()
    except Exception:
        logger.exception("tick_error", worker_id=_worker_id)
    finally:
        if acquired:
            try:
                await lock.release()
            except Exception:
                logger.warning("lock_release_failed", worker_id=_worker_id)
        await redis.aclose()