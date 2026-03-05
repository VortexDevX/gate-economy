# Phase 6 Summary: Guilds

**Status:** ✅ Complete
**Tests added:** 19 (12 simulation-level, 7 API-level)
**Cumulative tests:** 109

---

## What Was Built

Player-created economic organizations (guilds) with their own treasuries,
shares, dividends, gate investments, maintenance costs, and a full
insolvency → dissolution lifecycle. Guild shares trade on the same market
system as gate shares.

---

## New Tables

| Table                 | Purpose                                                        |
| --------------------- | -------------------------------------------------------------- |
| `guilds`              | Guild entity with treasury, status, policy                     |
| `guild_members`       | Player membership with role (LEADER/OFFICER/MEMBER)            |
| `guild_shares`        | Fractional ownership of guild equity                           |
| `guild_gate_holdings` | Gate shares owned by guilds (separate from player gate_shares) |

### Modified Tables

| Table    | Change                                          |
| -------- | ----------------------------------------------- |
| `orders` | Added `guild_id UUID NULL` — marks guild orders |

---

## New Enums

| Enum             | Values                             |
| ---------------- | ---------------------------------- |
| `GuildStatus`    | `ACTIVE`, `INSOLVENT`, `DISSOLVED` |
| `GuildRole`      | `LEADER`, `OFFICER`, `MEMBER`      |
| `DividendPolicy` | `MANUAL`, `AUTO_FIXED_PCT`         |

---

## Config Parameters Added

| Parameter                      | Default    | Purpose                                    |
| ------------------------------ | ---------- | ------------------------------------------ |
| `guild_creation_cost_micro`    | 50,000,000 | Cost to create a guild (50 currency)       |
| `guild_total_shares`           | 1,000      | Shares issued per guild                    |
| `guild_max_float_pct`          | 0.49       | Max public float (founder keeps majority)  |
| `guild_base_maintenance_micro` | 100,000    | Base per-tick maintenance (0.1 currency)   |
| `guild_maintenance_scale`      | 0.001      | Scale factor on gate holding value         |
| `guild_insolvency_threshold`   | 3          | Consecutive missed maintenance → INSOLVENT |
| `guild_dissolution_threshold`  | 10         | Consecutive insolvent ticks → DISSOLVED    |
| `guild_liquidation_discount`   | 0.50       | Liquidation price = market × 50%           |

---

## Economic Flows Added

| Flow    | Mechanism              | Direction         | Entry Type        |
| ------- | ---------------------- | ----------------- | ----------------- |
| Sink    | Guild creation fee     | Player → Treasury | GUILD_CREATION    |
| Sink    | Guild maintenance      | Guild → Treasury  | GUILD_MAINTENANCE |
| Faucet  | Yield to guild         | Treasury → Guild  | YIELD_PAYMENT     |
| Faucet  | Dividends              | Guild → Players   | DIVIDEND          |
| Lock    | Guild buy escrow       | Guild → Treasury  | ESCROW_LOCK       |
| Unlock  | Guild escrow release   | Treasury → Guild  | ESCROW_RELEASE    |
| Neutral | Guild share trades     | Player ↔ Player   | TRADE_SETTLEMENT  |
| Sink    | Guild share trade fees | Player → Treasury | TRADE_FEE         |

### Conservation Invariant Updated

```
treasury + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED
```

---

## API Endpoints Added

| Method | Path         | Auth | Purpose                                 |
| ------ | ------------ | ---- | --------------------------------------- |
| GET    | /guilds      | No   | List guilds (filter by status, paged)   |
| GET    | /guilds/{id} | No   | Detail: members, holdings, shareholders |

Guild creation and operations use existing `/intents` endpoint:

- `CREATE_GUILD` — name, public_float_pct, dividend_policy, auto_dividend_pct
- `GUILD_DIVIDEND` — guild_id, amount_micro (optional)
- `GUILD_INVEST` — guild_id, gate_id, quantity, price_limit_micro

---

## Tick Pipeline Changes

```
6.  Process intents: + CREATE_GUILD, GUILD_DIVIDEND, GUILD_INVEST
7.  Advance gates (spawn, lifecycle, yield — now includes guild gate holdings)
7b. Guild lifecycle (maintenance, insolvency, auto-dividends) ← NEW
8.  Create ISO orders (gates + guild shares) ← EXTENDED
9.  Cancel orders (collapsed gates + dissolved guilds) ← EXTENDED
10. Match orders (handles GUILD_SHARE + guild orders)
```

---

## Files Added

| File                            | Purpose                                                 |
| ------------------------------- | ------------------------------------------------------- |
| `app/models/guild.py`           | Guild, GuildMember, GuildShare, GuildGateHolding models |
| `app/services/guild_manager.py` | Creation, dividends, invest, maintenance, dissolution   |
| `app/schemas/guild.py`          | API response schemas                                    |
| `app/api/guilds.py`             | GET /guilds, GET /guilds/{id}                           |
| `tests/test_guild_manager.py`   | 12 simulation-level tests                               |
| `tests/test_guild_api.py`       | 7 API-level tests                                       |
| Migration: `add guilds...`      | New tables + guild_id on orders                         |

## Files Modified

| File                         | Change                                                              |
| ---------------------------- | ------------------------------------------------------------------- |
| `models/market.py`           | Added `guild_id` field to Order                                     |
| `models/__init__.py`         | Registered guild models                                             |
| `config.py`                  | Added 8 guild config parameters                                     |
| `services/transfer.py`       | Added GUILD case to `_load_and_lock()`                              |
| `services/gate_lifecycle.py` | Yield distribution includes guild holdings + 50% insolvency penalty |
| `services/order_matching.py` | GUILD_SHARE validation, ISOs, trade execution, cancellation         |
| `simulation/tick.py`         | Wired guild intents + guild lifecycle step                          |
| `simulation/state_hash.py`   | Added guild treasury sum + status counts                            |
| `main.py`                    | Registered guilds router                                            |
| `tests/conftest.py`          | Added guild table cleanup to `_reset_database`                      |
| `tests/test_conservation.py` | Added guild treasuries to invariant sum                             |
| `tests/test_tick.py`         | Updated intent test (no longer no-op)                               |

---

## Key Design Decisions

| Decision                               | Rationale                                            |
| -------------------------------------- | ---------------------------------------------------- |
| Guild `balance_micro` property         | Maps to `treasury_micro`, TransferService unchanged  |
| `guild_shares.player_id` no FK         | Same UUID convention — guild holds own ISO float     |
| Guild ISO price = creation_cost/shares | Fair baseline; market reprices via supply/demand     |
| ISO proceeds → guild treasury          | Proper IPO model — capital for guild, not founder    |
| Separate `guild_gate_holdings` table   | Clean separation from player gate shares             |
| Maintenance = base + scaled            | Small guilds pay base; large guilds pay more         |
| Insolvency = 50% yield penalty         | Punitive but not fatal; recovery possible            |
| Dissolution liquidates at 50% discount | Penalty for mismanagement; simpler than market sells |
| No seller fee on guild ISO             | Same as gate ISO — bootstrap, fee would be circular  |

---

## Guild Lifecycle

```
ACTIVE → (missed maintenance × threshold) → INSOLVENT
INSOLVENT → (pays maintenance) → ACTIVE (recovery)
INSOLVENT → (insolvent × threshold) → DISSOLVED (terminal)

Dissolution:
1. Liquidate gate holdings at 50% market price
2. Cancel guild's open orders, release escrow
3. Distribute remaining treasury to shareholders pro-rata
4. Cancel all GUILD_SHARE orders, release buyer escrow
5. Sweep any remainder to system treasury
```

---

## Test Coverage

### Simulation-Level (test_guild_manager.py)

- Guild creation: fee deduction, shares, membership
- Duplicate name rejection
- Insufficient balance rejection
- Guild ISO order creation
- Manual dividend distribution
- Non-leader dividend rejection
- Auto-dividend per-tick execution
- Guild invest → gate share acquisition
- Guild yield from gate holdings
- Insolvent guild yield penalty (50%) + recovery
- Full insolvency → dissolution → order cancellation
- Conservation invariant after guild operations

### API-Level (test_guild_api.py)

- List guilds (empty, populated, filtered, paginated)
- Invalid status filter → 400
- Guild detail with members, holdings, shareholder count
- Nonexistent guild → 404
