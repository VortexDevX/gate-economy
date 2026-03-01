# Phase 2 Sub-Plan: Identity, Wallet & Ledger

## Approach

11 steps, strictly sequential. Each step produces files that the next step depends on. No circular dependencies, no backtracking.

---

### Step 1 — Models

Create three model files, update `__init__.py`.

| File                 | Contents                                                                                                                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/player.py`   | `Player` — UUID PK, username, email, password_hash, balance_micro (BIGINT, CHECK >= 0), is_ai, timestamps                                                                                |
| `models/treasury.py` | `SystemAccount` — UUID PK, account_type ENUM('TREASURY'), balance_micro (BIGINT, CHECK >= 0), timestamps                                                                                 |
| `models/ledger.py`   | `LedgerEntry` — BIGSERIAL PK, tick_id (nullable), debit_type/debit_id, credit_type/credit_id, amount_micro (CHECK > 0), entry_type ENUM, memo, created_at. **No update/delete methods.** |
| `models/__init__.py` | Add imports for all three models so Alembic sees them                                                                                                                                    |

Enums defined: `AccountType`, `EntryType` (all 13 values from PLAN.md).

---

### Step 2 — Migration

```
make migration msg="add players, system_accounts, ledger_entries"
make migrate
```

Verify tables exist. No code to write — just run commands.

---

### Step 3 — Treasury Seeding

Add a startup hook in `main.py` lifespan: on startup, check if treasury row exists. If not, INSERT with `balance_micro = INITIAL_SEED`. Idempotent — safe on restart.

---

### Step 4 — Auth Core (`core/auth.py`)

| Function                                | Purpose                                   |
| --------------------------------------- | ----------------------------------------- |
| `hash_password(plain) → str`            | Argon2id hash                             |
| `verify_password(plain, hash) → bool`   | Argon2id verify                           |
| `create_access_token(player_id) → str`  | JWT, 15 min expiry                        |
| `create_refresh_token(player_id) → str` | JWT, 7 day expiry                         |
| `decode_token(token) → payload`         | Verify + decode, raise on expired/invalid |

No DB access. Pure utility functions.

---

### Step 5 — TransferService (`services/transfer.py`)

Single method:

```
async def transfer(session, from_type, from_id, to_type, to_id, amount, entry_type, memo, tick_id=None)
```

Inside one transaction:

1. `SELECT FOR UPDATE` source account (Player or SystemAccount based on type)
2. Assert `balance >= amount`
3. Debit source
4. Credit destination
5. INSERT `LedgerEntry`
6. Return the ledger entry

Raises `InsufficientBalance` on failure. No partial state ever committed.

---

### Step 6 — Auth Service (`services/auth.py`)

| Method                                | Logic                                                                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `register(username, email, password)` | Validate uniqueness → create Player → call `TransferService.transfer(TREASURY → PLAYER, starting_balance, STARTING_GRANT)` → return player |
| `login(email, password)`              | Lookup player → verify password → return access + refresh tokens                                                                           |
| `refresh(refresh_token)`              | Decode → verify player exists → return new access token                                                                                    |

Registration and starting grant happen in the **same DB transaction**.

---

### Step 7 — Schemas (`schemas/auth.py`, `schemas/player.py`)

| Schema                | Fields                                                            |
| --------------------- | ----------------------------------------------------------------- |
| `RegisterRequest`     | username, email, password (validated)                             |
| `LoginRequest`        | email, password                                                   |
| `RefreshRequest`      | refresh_token                                                     |
| `TokenResponse`       | access_token, refresh_token, token_type                           |
| `PlayerResponse`      | id, username, balance_micro, created_at                           |
| `LedgerEntryResponse` | id, amount_micro, entry_type, memo, created_at, debit/credit info |
| `PaginatedLedger`     | items, total, page, size                                          |

---

### Step 8 — Auth Dependency (`core/deps.py`)

Add `get_current_player(token, db)`:

- Extract `Authorization: Bearer <token>` header
- Decode JWT
- Load Player from DB by ID
- Raise 401 if missing/expired/invalid
- Return Player object for injection into routes

---

### Step 9 — API Routes

| File             | Endpoints                                                                      |
| ---------------- | ------------------------------------------------------------------------------ |
| `api/auth.py`    | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`                |
| `api/players.py` | `GET /players/me` (protected), `GET /players/me/ledger` (protected, paginated) |

---

### Step 10 — Wire into `main.py`

Add `auth_router` and `players_router` to `create_app()`. Add treasury seeding to lifespan.

---

### Step 11 — Tests

| Test file              | Cases                                                                                                                                          |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_transfer.py`     | Successful transfer, insufficient balance rollback, amount=0 rejected, negative amount rejected                                                |
| `test_auth.py`         | Register success, duplicate email/username rejected, login success, wrong password rejected, protected route without token → 401, refresh flow |
| `test_conservation.py` | Register N players → assert `treasury + SUM(player balances) == INITIAL_SEED`                                                                  |

---

## Execution Order Summary

```
Step 1:  models          → 4 files
Step 2:  migration       → commands only
Step 3:  treasury seed   → modify main.py
Step 4:  core/auth.py    → 1 file
Step 5:  transfer svc    → 1 file
Step 6:  auth svc        → 1 file
Step 7:  schemas         → 2 files
Step 8:  deps update     → modify deps.py
Step 9:  API routes      → 2 files
Step 10: wire main.py    → modify main.py
Step 11: tests           → 3 files
```

**Total: ~12 new files, ~3 modified files.**
