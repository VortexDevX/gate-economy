# Phase 2 — Complete ✓

## Summary of What We Built

### Database Tables

| Table               | Purpose                     | Key Constraints                                           |
| ------------------- | --------------------------- | --------------------------------------------------------- |
| **players**         | Player accounts with wallet | `balance_micro >= 0`, unique username, unique email       |
| **system_accounts** | Treasury (singleton)        | `balance_micro >= 0`, unique `account_type`               |
| **ledger_entries**  | Append-only audit trail     | `amount_micro > 0`, no UPDATE/DELETE in application layer |

### Enums Created

| Enum                | Values                                                                                                                                                                                                                                        |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AccountType`       | `TREASURY`                                                                                                                                                                                                                                    |
| `AccountEntityType` | `PLAYER`, `SYSTEM`, `GUILD`                                                                                                                                                                                                                   |
| `EntryType`         | `STARTING_GRANT`, `YIELD_PAYMENT`, `TRADE_SETTLEMENT`, `TRADE_FEE`, `GATE_DISCOVERY`, `GUILD_CREATION`, `GUILD_MAINTENANCE`, `PORTFOLIO_MAINTENANCE`, `CONCENTRATION_PENALTY`, `LIQUIDITY_DECAY`, `DIVIDEND`, `AI_BUDGET`, `ADMIN_ADJUSTMENT` |

### Services

| Service             | Method                   | Purpose                                                                                      |
| ------------------- | ------------------------ | -------------------------------------------------------------------------------------------- |
| **TransferService** | `transfer()`             | Atomic double-entry: SELECT FOR UPDATE → debit → credit → ledger INSERT. Single transaction. |
| **AuthService**     | `register()`             | Create player + starting grant from treasury in one transaction                              |
| **AuthService**     | `login()`                | Verify credentials → return JWT access + refresh tokens                                      |
| **AuthService**     | `refresh_access_token()` | Validate refresh token → issue new access token                                              |

### Auth System

| Component        | Detail                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------- |
| Password hashing | Argon2id via `argon2-cffi`                                                               |
| Access token     | JWT, 15 min expiry, `type: "access"`                                                     |
| Refresh token    | JWT, 7 day expiry, `type: "refresh"`                                                     |
| Auth dependency  | `get_current_player()` — extracts Bearer token, loads Player from DB, injects into route |

### API Endpoints

| Method | Path                 | Auth | Purpose                                |
| ------ | -------------------- | ---- | -------------------------------------- |
| `GET`  | `/health`            | No   | Health check                           |
| `GET`  | `/ready`             | No   | DB + Redis connectivity                |
| `POST` | `/auth/register`     | No   | Create account, grant starting balance |
| `POST` | `/auth/login`        | No   | Returns access + refresh tokens        |
| `POST` | `/auth/refresh`      | No   | New access token from refresh token    |
| `GET`  | `/players/me`        | Yes  | Profile + balance                      |
| `GET`  | `/players/me/ledger` | Yes  | Paginated personal ledger              |

### Treasury Seeding

- On API startup, checks for treasury row — creates with `INITIAL_SEED` (100B micro-units) if absent
- Idempotent — safe on restart

### Testing

| Test File              | Tests         | Covers                                                                                                                                                                                                          |
| ---------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_health.py`       | 2             | Health + ready endpoints                                                                                                                                                                                        |
| `test_transfer.py`     | 4             | Successful transfer, insufficient balance rollback, zero amount rejected, negative amount rejected                                                                                                              |
| `test_auth.py`         | 12            | Register success, duplicate username, duplicate email, short password, login success, wrong password, nonexistent email, no token → 403, invalid token → 401, profile retrieval, ledger retrieval, refresh flow |
| `test_conservation.py` | 1             | Register 5 players → `treasury + SUM(players) = INITIAL_SEED`                                                                                                                                                   |
| **Total**              | **19 passed** |                                                                                                                                                                                                                 |

### Infrastructure Fix: Async Test Setup

| Problem                                                      | Root Cause                                                                             | Solution                                                                  |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `cannot perform operation: another operation is in progress` | Module-level engine created at import time bound connections to wrong event loop       | Lazy engine init in `database.py` + NullPool per-fixture engines in tests |
| `Future attached to a different loop`                        | pytest-asyncio creates new event loop per test, pooled connections bound to prior loop | Each test fixture creates its own `NullPool` engine, fully self-contained |

### Files Created or Modified (Phase 2)

```
backend/app/
├── config.py                    ← unchanged
├── database.py                  ← MODIFIED: lazy engine/session factory init
├── main.py                      ← MODIFIED: treasury seeding + auth/players routers
├── models/
│   ├── __init__.py              ← MODIFIED: register all models
│   ├── base.py                  ← unchanged
│   ├── player.py                ← NEW
│   ├── treasury.py              ← NEW
│   └── ledger.py                ← NEW
├── schemas/
│   ├── auth.py                  ← NEW
│   └── player.py                ← NEW
├── services/
│   ├── transfer.py              ← NEW
│   └── auth.py                  ← NEW
├── api/
│   ├── health.py                ← unchanged
│   ├── auth.py                  ← NEW
│   └── players.py               ← NEW
├── core/
│   ├── deps.py                  ← MODIFIED: get_current_player + lazy imports
│   └── auth.py                  ← NEW
└── tests/
    ├── conftest.py              ← MODIFIED: NullPool fixtures
    ├── test_health.py           ← unchanged
    ├── test_transfer.py         ← NEW
    ├── test_auth.py             ← NEW
    └── test_conservation.py     ← NEW

backend/
├── requirements.txt             ← MODIFIED: added email-validator
├── pyproject.toml               ← MODIFIED: filterwarnings
└── alembic/versions/
    └── 9db8473f1dcd_...py       ← NEW: migration
```

### Economic Invariant Status

```
✅ treasury_balance + SUM(player_balances) = INITIAL_SEED
   Verified by test_conservation after 5 registrations.
   No guild treasuries yet (Phase 6).
```

### Architecture Checkpoint

```
Phase 1 ✅ — Foundation & Infrastructure
Phase 2 ✅ — Identity, Wallet & Ledger
Phase 3 ⬜ — Simulation Engine Core          ← NEXT
```

---

**Phase 2 acceptance criteria — all met:**

- ✅ Registration → player gets starting balance, treasury debited
- ✅ Double registration rejected
- ✅ Login returns valid tokens, protected routes work
- ✅ `transfer()` with insufficient balance → rollback, no state change
- ✅ Conservation test passes
- ✅ Ledger is append-only (no UPDATE/DELETE path in service layer)
