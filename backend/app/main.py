import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.auth import router as auth_router
from app.api.gates import router as gates_router
from app.api.health import router as health_router
from app.api.intents import router as intents_router
from app.api.players import router as players_router
from app.api.simulation import router as simulation_router
from app.config import settings
from app.database import get_session_factory
from app.models.gate import GateRank, GateRankProfile
from app.models.treasury import AccountType, SystemAccount


def setup_logging() -> None:
    """Configure structlog for JSON output to stdout."""
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


async def seed_treasury() -> None:
    """Create treasury account with INITIAL_SEED if it doesn't exist."""
    log = structlog.get_logger()
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(SystemAccount).where(
                SystemAccount.account_type == AccountType.TREASURY
            )
        )
        treasury = result.scalar_one_or_none()
        if treasury is None:
            treasury = SystemAccount(
                account_type=AccountType.TREASURY,
                balance_micro=settings.initial_seed_micro,
            )
            session.add(treasury)
            await session.commit()
            log.info(
                "treasury_seeded",
                balance_micro=settings.initial_seed_micro,
            )
        else:
            log.info(
                "treasury_exists",
                balance_micro=treasury.balance_micro,
            )


async def seed_gate_rank_profiles() -> None:
    """Seed gate rank profiles if table is empty. Idempotent."""
    log = structlog.get_logger()
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(GateRankProfile).limit(1))
        if result.scalar_one_or_none() is not None:
            log.info("gate_rank_profiles_exist")
            return

        profiles = [
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
            ),
            GateRankProfile(
                rank=GateRank.D,
                stability_init=95.0,
                volatility=0.08,
                yield_min_micro=3_000,
                yield_max_micro=10_000,
                total_shares=80,
                lifespan_min=180,
                lifespan_max=360,
                collapse_threshold=22.0,
                discovery_cost_micro=250_000,
                spawn_weight=25,
            ),
            GateRankProfile(
                rank=GateRank.C,
                stability_init=90.0,
                volatility=0.12,
                yield_min_micro=8_000,
                yield_max_micro=25_000,
                total_shares=60,
                lifespan_min=150,
                lifespan_max=300,
                collapse_threshold=25.0,
                discovery_cost_micro=500_000,
                spawn_weight=18,
            ),
            GateRankProfile(
                rank=GateRank.B,
                stability_init=85.0,
                volatility=0.15,
                yield_min_micro=20_000,
                yield_max_micro=60_000,
                total_shares=50,
                lifespan_min=120,
                lifespan_max=250,
                collapse_threshold=28.0,
                discovery_cost_micro=1_000_000,
                spawn_weight=10,
            ),
            GateRankProfile(
                rank=GateRank.A,
                stability_init=80.0,
                volatility=0.20,
                yield_min_micro=50_000,
                yield_max_micro=150_000,
                total_shares=40,
                lifespan_min=100,
                lifespan_max=200,
                collapse_threshold=30.0,
                discovery_cost_micro=2_500_000,
                spawn_weight=5,
            ),
            GateRankProfile(
                rank=GateRank.S,
                stability_init=75.0,
                volatility=0.25,
                yield_min_micro=120_000,
                yield_max_micro=400_000,
                total_shares=30,
                lifespan_min=80,
                lifespan_max=160,
                collapse_threshold=35.0,
                discovery_cost_micro=5_000_000,
                spawn_weight=2,
            ),
            GateRankProfile(
                rank=GateRank.S_PLUS,
                stability_init=70.0,
                volatility=0.30,
                yield_min_micro=300_000,
                yield_max_micro=1_000_000,
                total_shares=20,
                lifespan_min=60,
                lifespan_max=120,
                collapse_threshold=40.0,
                discovery_cost_micro=10_000_000,
                spawn_weight=1,
            ),
        ]
        session.add_all(profiles)
        await session.commit()
        log.info("gate_rank_profiles_seeded", count=len(profiles))


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log = structlog.get_logger()
    log.info("application_startup", version=app.version)
    await seed_treasury()
    await seed_gate_rank_profiles()
    yield
    log.info("application_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dungeon Gate Economy",
        version="0.1.0",
        docs_url="/docs",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ──
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log = structlog.get_logger()
        log.error(
            "unhandled_exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ── Routers ──
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(players_router)
    app.include_router(intents_router)
    app.include_router(simulation_router)
    app.include_router(gates_router)

    return app


app = create_app()