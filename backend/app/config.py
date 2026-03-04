from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──
    database_url: str = "postgresql+asyncpg://dge:dge_dev@postgres:5432/dungeon_gate"

    # ── Redis ──
    redis_url: str = "redis://redis:6379/0"

    # ── Auth ──
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # ── Economy ──
    initial_seed_micro: int = 100_000_000_000  # 100,000 currency in micro-units
    starting_balance_micro: int = 10_000_000    # 10 currency in micro-units

    # ── Simulation ──
    simulation_initial_seed: int = 42
    simulation_tick_interval: int = 5  # seconds between ticks

    # ── Gate Settings ──
    system_spawn_probability: float = 0.15   # chance per tick of system gate spawn
    gate_offering_ticks: int = 60            # ticks in OFFERING before ACTIVE
    gate_base_decay_rate: float = 0.1        # base stability decay per tick

    # ── Market Fees ──
    base_fee_rate: float = 0.005             # 0.5% minimum fee rate
    progressive_fee_rate: float = 0.5        # scaling factor for progressive fees
    fee_scale_micro: int = 10_000_000        # denominator for progressive scaling (10 currency)
    max_fee_rate: float = 0.10               # 10% hard cap on fee rate
    iso_payback_ticks: int = 100             # ticks of yield used to price ISO shares

    # ── Celery ──
    celery_broker_url: str = "redis://redis:6379/0"

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()