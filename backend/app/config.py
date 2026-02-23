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

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
