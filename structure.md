📁 dungeon-gate-economy/
├── 📁 .github/
│   └── 📁 workflows/
│       └── 📄 ci.yml
├── 📁 backend/
│   ├── 📁 alembic/
│   │   ├── 📁 versions/
│   │   │   ├── 📄 .gitkeep
│   │   │   └── 📄 9db8473f1dcd_add_players_system_accounts_ledger_.py
│   │   ├── 📄 env.py
│   │   └── 📄 script.py.mako
│   ├── 📁 app/
│   │   ├── 📁 api/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   ├── 📄 health.py
│   │   │   └── 📄 players.py
│   │   ├── 📁 core/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 deps.py
│   │   ├── 📁 models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py
│   │   │   ├── 📄 ledger.py
│   │   │   ├── 📄 player.py
│   │   │   └── 📄 treasury.py
│   │   ├── 📁 schemas/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 player.py
│   │   ├── 📁 services/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py
│   │   │   └── 📄 transfer.py
│   │   ├── 📁 simulation/
│   │   │   └── 📄 __init__.py
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
│   │   └── 📄 PLAN.md
│   ├── 📁 summary/
│   │   ├── 📄 SUMMARY_1.md
│   │   └── 📄 SUMMARY_2.md
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
├── 📄 input.txt
└── 📄 output.txt
