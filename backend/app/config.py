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
    
    # ── Guild Settings ──
    guild_creation_cost_micro: int = 50_000_000       # 50 currency
    guild_total_shares: int = 1000
    guild_max_float_pct: float = 0.49
    guild_base_maintenance_micro: int = 100_000       # 0.1 currency per tick
    guild_maintenance_scale: float = 0.001
    guild_insolvency_threshold: int = 3               # missed ticks → INSOLVENT
    guild_dissolution_threshold: int = 10             # insolvent ticks → DISSOLVED
    guild_liquidation_discount: float = 0.50

    # ── AI Trader Settings ──
    ai_market_maker_budget_micro: int = 2_000_000_000   # 2,000 currency
    ai_value_investor_budget_micro: int = 1_000_000_000  # 1,000 currency
    ai_noise_trader_budget_micro: int = 500_000_000      # 500 currency
    ai_mm_spread: float = 0.05                           # 5% bid/ask spread
    ai_mm_order_qty: int = 5                             # shares per MM order
    ai_vi_buy_discount: float = 0.30                     # buy when price < fair*(1-this)
    ai_vi_sell_premium: float = 0.30                     # sell when price > fair*(1+this)
    ai_noise_activity: float = 0.40                      # probability NT acts per tick
    ai_noise_max_qty: int = 3                            # max shares per noise trade
    
    # ── Event Settings ──
    event_probability: float = 0.10
    event_stability_surge_min: float = 5.0
    event_stability_surge_max: float = 15.0
    event_stability_crisis_min: float = 5.0
    event_stability_crisis_max: float = 15.0
    event_market_shock_min: float = 2.0
    event_market_shock_max: float = 5.0
    event_yield_boom_min_multiplier: float = 2.0
    event_yield_boom_max_multiplier: float = 4.0
    event_discovery_surge_min: int = 1
    event_discovery_surge_max: int = 3
    news_large_trade_threshold_micro: int = 1_000_000

    # ── Anti-Exploit Settings ──
    portfolio_maintenance_rate: float = 0.0001        # 0.01% of holding value per tick
    concentration_threshold_pct: float = 0.30         # penalty above 30% ownership
    concentration_penalty_rate: float = 0.001         # 0.1% of holding value per tick
    liquidity_decay_inactive_ticks: int = 200         # ticks without trade → illiquid
    liquidity_decay_rate: float = 0.0005              # 0.05% of holding value per tick
    max_player_ownership_pct: float = 0.50            # max 50% of any gate's shares

    # ── Leaderboard & Seasons ──
    net_worth_update_interval: int = 12                   # update every N ticks (~1 min)
    leaderboard_size: int = 100                           # max entries returned by API
    leaderboard_decay_rate: float = 0.0001                # 0.01% score decay per inactive tick
    leaderboard_decay_inactive_ticks: int = 100           # grace period before decay
    leaderboard_decay_floor: float = 0.50                 # min decay multiplier (50%)
    season_duration_ticks: int = 17280                    # ~1 day at 5s/tick
    
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