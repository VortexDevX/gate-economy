```
📁 dungeon-gate-economy/
├── 📁 .github/
│   └── 📁 workflows/
│       └── 📄 ci.yml
├── 📁 backend/
│   ├── 📁 alembic/
│   │   ├── 📁 versions/
│   │   │   ├── 📄 .gitkeep
│   │   │   ├── 📄 9db8473f1dcd_add_players_system_accounts_ledger_.py
│   │   │   └── 📄 af99e45efd47_add_ticks_and_intents.py
│   │   ├── 📄 env.py
│   │   └── 📄 script.py.mako
│   ├── 📁 app/
│   │   ├── 📁 api/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 health.py
│   │   │   ├── 📄 intents.py
│   │   │   ├── 📄 players.py
│   │   │   └── 📄 simulation.py
│   │   ├── 📁 core/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 deps.py
│   │   ├── 📁 models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 ledger.py
│   │   │   ├── 📄 player.py
│   │   │   ├── 📄 tick.py
│   │   │   └── 📄 treasury.py
│   │   ├── 📁 schemas/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 intent.py
│   │   │   ├── 📄 player.py
│   │   │   └── 📄 simulation.py
│   │   ├── 📁 services/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
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
│   │   ├── 📄 test_health.py
│   │   ├── 📄 test_intents_api.py
│   │   ├── 📄 test_lock.py
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
│   │   └── 📄 PLAN.md
│   ├── 📁 postman/
│   │   └── 📄 DungeonGateEconomy.postman_collection.json
│   ├── 📁 summary/
│   │   ├── 📄 SUMMARY_1.md
│   │   ├── 📄 SUMMARY_2.md
│   │   └── 📄 SUMMARY_3.md
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
```
