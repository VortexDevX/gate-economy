📁 dungeon-gate-economy/
├── 📁 backend/
│   ├── 📁 alembic/
│   │   ├── 📁 versions/
│   │   │   ├── 📄 .gitkeep
│   │   │   ├── 📄 0077d445e221_add_gates_gate_rank_profiles_gate_shares.py
│   │   │   ├── 📄 2e9f2d2c75d9_add_admin_role_and_simulation_parameters.py
│   │   │   ├── 📄 4df4626355da_add_leaderboard_and_seasons.py
│   │   │   ├── 📄 7030291f0b68_add_orders_trades_market_prices_and_.py
│   │   │   ├── 📄 8921b1e0d286_add_events_and_news.py
│   │   │   ├── 📄 9db8473f1dcd_add_players_system_accounts_ledger_.py
│   │   │   ├── 📄 af99e45efd47_add_ticks_and_intents.py
│   │   │   └── 📄 f1da578fa5fc_add_guilds_guild_members_guild_shares_.py
│   │   ├── 📄 env.py
│   │   └── 📄 script.py.mako
│   ├── 📁 app/
│   │   ├── 📁 api/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 admin.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 events.py
│   │   │   ├── 📄 gates.py
│   │   │   ├── 📄 guilds.py
│   │   │   ├── 📄 health.py
│   │   │   ├── 📄 intents.py
│   │   │   ├── 📄 leaderboard.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 metrics.py
│   │   │   ├── 📄 news.py
│   │   │   ├── 📄 orders.py
│   │   │   ├── 📄 players.py
│   │   │   ├── 📄 simulation.py
│   │   │   └── 📄 ws.py
│   │   ├── 📁 core/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 admin.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 deps.py
│   │   ├── 📁 models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 admin.py
│   │   │   ├── 📄 base.py
│   │   │   ├── 📄 event.py
│   │   │   ├── 📄 gate.py
│   │   │   ├── 📄 guild.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 leaderboard.py
│   │   │   ├── 📄 ledger.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 news.py
│   │   │   ├── 📄 player.py
│   │   │   ├── 📄 tick.py
│   │   │   └── 📄 treasury.py
│   │   ├── 📁 schemas/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 admin.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 event.py
│   │   │   ├── 📄 gate.py
│   │   │   ├── 📄 guild.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 leaderboard.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 news.py
│   │   │   ├── 📄 player.py
│   │   │   └── 📄 simulation.py
│   │   ├── 📁 services/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 admin.py
│   │   │   ├── 📄 ai_traders.py
│   │   │   ├── 📄 anti_exploit.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 event_engine.py
│   │   │   ├── 📄 fee_calculator.py
│   │   │   ├── 📄 gate_lifecycle.py
│   │   │   ├── 📄 guild_manager.py
│   │   │   ├── 📄 leaderboard.py
│   │   │   ├── 📄 news_generator.py
│   │   │   ├── 📄 order_matching.py
│   │   │   ├── 📄 realtime.py
│   │   │   └── 📄 transfer.py
│   │   ├── 📁 simulation/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 lock.py
│   │   │   ├── 📄 rng.py
│   │   │   ├── 📄 state_hash.py
│   │   │   ├── 📄 tick.py
│   │   │   └── 📄 worker.py
│   │   ├── 📄 __init__.py
│   │   ├── 📄 config.py
│   │   ├── 📄 database.py
│   │   └── 📄 main.py
│   ├── 📁 tests/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 conftest.py
│   │   ├── 📄 test_admin.py
│   │   ├── 📄 test_ai_traders.py
│   │   ├── 📄 test_anti_exploit.py
│   │   ├── 📄 test_auth.py
│   │   ├── 📄 test_conservation.py
│   │   ├── 📄 test_events.py
│   │   ├── 📄 test_events_api.py
│   │   ├── 📄 test_fee_calculator.py
│   │   ├── 📄 test_gates.py
│   │   ├── 📄 test_gates_api.py
│   │   ├── 📄 test_guild_api.py
│   │   ├── 📄 test_guild_manager.py
│   │   ├── 📄 test_health.py
│   │   ├── 📄 test_intents_api.py
│   │   ├── 📄 test_leaderboard.py
│   │   ├── 📄 test_lock.py
│   │   ├── 📄 test_market.py
│   │   ├── 📄 test_market_api.py
│   │   ├── 📄 test_news.py
│   │   ├── 📄 test_replay.py
│   │   ├── 📄 test_rng.py
│   │   ├── 📄 test_tick.py
│   │   ├── 📄 test_transfer.py
│   │   └── 📄 test_ws.py
│   ├── 📄 .dockerignore
│   ├── 📄 Dockerfile
│   ├── 📄 alembic.ini
│   ├── 📄 pyproject.toml
│   └── 📄 requirements.txt
├── 📁 docs/
│   ├── 📁 plan/
│   │   ├── 📄 PHASE_10_PLAN.md
│   │   ├── 📄 PHASE_11_PLAN.md
│   │   ├── 📄 PHASE_2_PLAN.md
│   │   ├── 📄 PHASE_3_PLAN.md
│   │   ├── 📄 PHASE_4_PLAN.md
│   │   ├── 📄 PHASE_5_PLAN.md
│   │   ├── 📄 PHASE_6_PLAN.md
│   │   ├── 📄 PHASE_7_PLAN.md
│   │   ├── 📄 PHASE_8_PLAN.md
│   │   ├── 📄 PHASE_9_PLAN.md
│   │   └── 📄 PLAN.md
│   ├── 📁 postman/
│   │   └── 📄 DungeonGateEconomy.postman_collection.json
│   ├── 📁 summary/
│   │   ├── 📄 SUMMARY_1.md
│   │   ├── 📄 SUMMARY_10.md
│   │   ├── 📄 SUMMARY_11.md
│   │   ├── 📄 SUMMARY_2.md
│   │   ├── 📄 SUMMARY_3.md
│   │   ├── 📄 SUMMARY_4.md
│   │   ├── 📄 SUMMARY_5.md
│   │   ├── 📄 SUMMARY_6.md
│   │   ├── 📄 SUMMARY_7.md
│   │   ├── 📄 SUMMARY_8.md
│   │   └── 📄 SUMMARY_9.md
│   ├── 📄 CONTEXT.md
│   ├── 📄 architecture.md
│   └── 📄 runbook.md
├── 📁 frontend/
│   ├── 📁 src/
│   └── 📄 .gitkeep
├── 📁 infra/
│   ├── 📁 grafana/
│   │   ├── 📁 dashboards/
│   │   │   └── 📄 dge-overview.json
│   │   └── 📁 provisioning/
│   │       ├── 📁 dashboards/
│   │       │   └── 📄 dashboard.yml
│   │       └── 📁 datasources/
│   │           └── 📄 datasource.yml
│   ├── 📁 k6/
│   │   ├── 📄 auth_load.js
│   │   ├── 📄 mixed_workload.js
│   │   ├── 📄 order_storm.js
│   │   └── 📄 ws_connections.js
│   └── 📄 prometheus.yml
├── 📄 .env.example
├── 📄 .gitignore
├── 📄 Makefile
├── 📄 docker-compose.yml
└── 📄 structure.md
