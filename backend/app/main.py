import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.intents import router as intents_router
from app.api.players import router as players_router
from app.api.simulation import router as simulation_router
from app.config import settings
from app.database import get_session_factory
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log = structlog.get_logger()
    log.info("application_startup", version=app.version)
    await seed_treasury()
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

    return app


app = create_app()