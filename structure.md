📁 dungeon-gate-economy/
├── 📁 .github/
│   └── 📁 workflows/
│       └── 📄 ci.yml
├── 📁 backend/
│   ├── 📁 alembic/
│   │   ├── 📁 versions/
│   │   │   ├── 📄 .gitkeep
│   │   │   ├── 📄 0077d445e221_add_gates_gate_rank_profiles_gate_shares.py
│   │   │   ├── 📄 7030291f0b68_add_orders_trades_market_prices_and_.py
│   │   │   ├── 📄 9db8473f1dcd_add_players_system_accounts_ledger_.py
│   │   │   └── 📄 af99e45efd47_add_ticks_and_intents.py
│   │   ├── 📄 env.py
│   │   └── 📄 script.py.mako
│   ├── 📁 app/
│   │   ├── 📁 api/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 gates.py
│   │   │   ├── 📄 health.py
│   │   │   ├── 📄 intents.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 orders.py
│   │   │   ├── 📄 players.py
│   │   │   └── 📄 simulation.py
│   │   ├── 📁 core/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 deps.py
│   │   ├── 📁 models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py
│   │   │   ├── 📄 gate.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 ledger.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 player.py
│   │   │   ├── 📄 tick.py
│   │   │   └── 📄 treasury.py
│   │   ├── 📁 schemas/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 gate.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 market.py
│   │   │   ├── 📄 player.py
│   │   │   └── 📄 simulation.py
│   │   ├── 📁 services/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 fee_calculator.py
│   │   │   ├── 📄 gate_lifecycle.py
│   │   │   ├── 📄 order_matching.py
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
│   │   ├── 📄 test_auth.py
│   │   ├── 📄 test_conservation.py
│   │   ├── 📄 test_fee_calculator.py
│   │   ├── 📄 test_gates.py
│   │   ├── 📄 test_gates_api.py
│   │   ├── 📄 test_health.py
│   │   ├── 📄 test_intents_api.py
│   │   ├── 📄 test_lock.py
│   │   ├── 📄 test_market.py
│   │   ├── 📄 test_market_api.py
│   │   ├── 📄 test_replay.py
│   │   ├── 📄 test_rng.py
│   │   ├── 📄 test_tick.py
│   │   └── 📄 test_transfer.py
│   ├── 📄 .dockerignore
│   ├── 📄 Dockerfile
│   ├── 📄 alembic.ini
│   ├── 📄 pyproject.toml
│   └── 📄 requirements.txt
├── 📁 docs/
│   ├── 📁 plan/
│   │   ├── 📄 PHASE_2_PLAN.md
│   │   ├── 📄 PHASE_3_PLAN.md
│   │   ├── 📄 PHASE_4_PLAN.md
│   │   ├── 📄 PHASE_5_PLAN.md
│   │   └── 📄 PLAN.md
│   ├── 📁 postman/
│   │   └── 📄 DungeonGateEconomy.postman_collection.json
│   ├── 📁 summary/
│   │   ├── 📄 SUMMARY_1.md
│   │   ├── 📄 SUMMARY_2.md
│   │   ├── 📄 SUMMARY_3.md
│   │   ├── 📄 SUMMARY_4.md
│   │   └── 📄 SUMMARY_5.md
│   ├── 📄 CONTEXT.md
│   ├── 📄 architecture.md
│   └── 📄 runbook.md
├── 📁 frontend/
│   ├── 📁 src/
│   └── 📄 .gitkeep
├── 📁 infra/
│   ├── 📁 grafana/
│   ├── 📁 k6/
│   └── 📄 prometheus.yml
├── 📄 .env.example
├── 📄 .gitignore
├── 📄 Makefile
├── 📄 docker-compose.yml
└── 📄 structure.md
