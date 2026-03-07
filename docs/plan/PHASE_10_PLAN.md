# Phase 10 Sub-Plan: Leaderboards & Seasons

## Goal

Implement a net-worth-based leaderboard with activity-based score decay and a seasonal competitive system. Players are ranked by a score derived from their total net worth (balance + portfolio value), with inactive players seeing their score erode over time. Seasons provide bounded competitive periods with recorded final standings.

---

## Economic Flows Introduced

| Flow | Mechanism | Direction | Entry Type |
| ---- | --------- | --------- | ---------- |
| —    | None      | —         | —          |

No new currency flows. Leaderboard and seasons are read/derived systems. Net worth is computed from existing state (balances, share holdings, market prices). No rewards in this phase (can be added later).

---

## Step 1 — Config

### Config Additions (`config.py`)

| Parameter                          | Default | Purpose                                         |
| ---------------------------------- | ------- | ----------------------------------------------- |
| `net_worth_update_interval`        | 12      | Update leaderboard every N ticks (~1 min at 5s) |
| `leaderboard_size`                 | 100     | Max entries returned by API                     |
| `leaderboard_decay_rate`           | 0.0001  | Score decay per inactive tick (0.01%)           |
| `leaderboard_decay_inactive_ticks` | 100     | Grace period before decay starts                |
| `leaderboard_decay_floor`          | 0.50    | Min decay multiplier (50% of net worth)         |
| `season_duration_ticks`            | 17280   | Ticks per season (~1 day at 5s/tick)            |

---

## Step 2 — Migration

New PostgreSQL enum:

```sql
CREATE TYPE seasonstatus AS ENUM ('ACTIVE', 'COMPLETED');
```

New tables:

### player_net_worth

```sql
CREATE TABLE player_net_worth (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    net_worth_micro BIGINT NOT NULL DEFAULT 0,
    score_micro BIGINT NOT NULL DEFAULT 0,
    balance_micro BIGINT NOT NULL DEFAULT 0,
    portfolio_micro BIGINT NOT NULL DEFAULT 0,
    last_active_tick INT NOT NULL DEFAULT 0,
    updated_at_tick INT NOT NULL DEFAULT 0
);
```

### seasons

```sql
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    season_number INT NOT NULL UNIQUE,
    start_tick INT NOT NULL,
    end_tick INT,
    status seasonstatus NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### season_results

```sql
CREATE TABLE season_results (
    season_id INT REFERENCES seasons(id),
    player_id UUID REFERENCES players(id),
    final_rank INT NOT NULL,
    final_score_micro BIGINT NOT NULL,
    final_net_worth_micro BIGINT NOT NULL,
    PRIMARY KEY (season_id, player_id)
);
```

---

## Step 3 — Models (`models/leaderboard.py`, 🆕 new file)

```python
class SeasonStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class PlayerNetWorth(Base):
    __tablename__ = "player_net_worth"
    player_id: UUID PK FK→players
    net_worth_micro: BIGINT default 0
    score_micro: BIGINT default 0
    balance_micro: BIGINT default 0
    portfolio_micro: BIGINT default 0
    last_active_tick: INT default 0
    updated_at_tick: INT default 0

class Season(Base):
    __tablename__ = "seasons"
    id: SERIAL PK
    season_number: INT UQ
    start_tick: INT
    end_tick: INT NULL
    status: SeasonStatus default ACTIVE
    created_at: TZ

class SeasonResult(Base):
    __tablename__ = "season_results"
    season_id: INT PK FK→seasons
    player_id: UUID PK FK→players
    final_rank: INT
    final_score_micro: BIGINT
    final_net_worth_micro: BIGINT
```

Register all three in `models/__init__.py`.

---

## Step 4 — Leaderboard Service (`services/leaderboard.py`, 🆕 new file)

### Helper: `_portfolio_value_micro(session, player_id, tick_number) → int`

Computes the total value of a player's share holdings:

```python
1. Load all GateShare rows for this player where gate is ACTIVE or UNSTABLE
2. Load all GuildShare rows for this player where guild is ACTIVE or INSOLVENT
3. Batch-load MarketPrice for all held assets
4. For each gate share:
   - per_share = market_price.last_price_micro or _share_value_micro(gate, market_price)
     (reuse _share_value_micro from anti_exploit.py)
   - value += quantity * per_share
5. For each guild share:
   - per_share = market_price.last_price_micro or (guild_creation_cost // guild_total_shares)
   - value += quantity * per_share
6. Return total value
```

### `_compute_last_active_tick(session, player_id) → int`

Derives last activity tick from most recent intent or order:

```python
1. Query MAX(processed_tick) from intents WHERE player_id = X AND status = EXECUTED
2. Query MAX(created_at_tick) from orders WHERE player_id = X AND is_system = FALSE
3. Return max of both (or 0 if no activity)
```

### `_apply_decay(net_worth_micro, tick_number, last_active_tick) → int`

Computes score with activity-based decay:

```python
inactive = max(0, tick_number - last_active_tick - settings.leaderboard_decay_inactive_ticks)
if inactive <= 0:
    return net_worth_micro
multiplier = max(settings.leaderboard_decay_floor, 1.0 - settings.leaderboard_decay_rate * inactive)
return int(net_worth_micro * multiplier)
```

### `update_leaderboard(session, tick_number, tick_id)`

Batch-update all player net worths and scores:

```python
1. Load all non-AI players
2. Batch-load all gate shares, guild shares, market prices
3. For each player:
   a. portfolio = sum of share values (gate + guild)
   b. net_worth = player.balance_micro + portfolio
   c. last_active = _compute_last_active_tick(session, player_id)
   d. score = _apply_decay(net_worth, tick_number, last_active)
   e. Upsert into player_net_worth table
```

### `check_season(session, tick_number, tick_id)`

Season lifecycle management:

```python
1. Load ACTIVE season
2. If no active season:
   - Create season(season_number=1, start_tick=tick_number, status=ACTIVE)
   - Return
3. If tick_number - season.start_tick >= settings.season_duration_ticks:
   - Call finalize_season(session, season, tick_number, tick_id)
   - Create new season(season_number=prev+1, start_tick=tick_number, status=ACTIVE)
```

### `finalize_season(session, season, tick_number, tick_id)`

Record final standings and complete the season:

```python
1. Force update_leaderboard (ensure fresh scores)
2. Load all player_net_worth rows ordered by score_micro DESC
3. For rank, entry in enumerate(entries, 1):
   - Insert SeasonResult(season_id, player_id, rank, score, net_worth)
4. Set season.status = COMPLETED, season.end_tick = tick_number
```

---

## Step 5 — Pipeline Wiring

### Update `simulation/tick.py`

Add import:

```python
from app.services.leaderboard import update_leaderboard, check_season
```

After step 14, add step 14b:

```python
# 14b. Leaderboard & season updates
await check_season(session, tick_number, tick.id)
if tick_number % settings.net_worth_update_interval == 0:
    await update_leaderboard(session, tick_number, tick.id)
```

---

## Step 6 — State Hash Extension

### Update `simulation/state_hash.py`

Add to the hash computation:

```python
# Season state
result = await session.execute(
    select(func.count(Season.id)).where(Season.status == SeasonStatus.ACTIVE)
)
active_seasons = result.scalar_one()

result = await session.execute(
    select(func.count(Season.id))
)
total_seasons = result.scalar_one()

# Append to hash input:
# f"seasons:{total_seasons}:{active_seasons}"
```

---

## Step 7 — API & Schemas

### Schemas (`schemas/leaderboard.py`, 🆕 new file)

```python
class LeaderboardEntry(BaseModel):
    rank: int
    player_id: UUID
    username: str
    score_micro: int
    net_worth_micro: int
    balance_micro: int
    portfolio_micro: int

class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    total: int
    page: int
    page_size: int

class MyRankResponse(BaseModel):
    rank: int | None
    player_id: UUID
    score_micro: int
    net_worth_micro: int
    balance_micro: int
    portfolio_micro: int
    last_active_tick: int
    updated_at_tick: int

class SeasonResponse(BaseModel):
    id: int
    season_number: int
    start_tick: int
    end_tick: int | None
    status: str

class SeasonDetailResponse(SeasonResponse):
    top_players: list[LeaderboardEntry]
```

### API Router (`api/leaderboard.py`, 🆕 new file)

| Method | Path               | Auth | Purpose                                 |
| ------ | ------------------ | ---- | --------------------------------------- |
| GET    | `/leaderboard`     | No   | Paginated rankings (non-AI players)     |
| GET    | `/leaderboard/me`  | Yes  | Authenticated player's rank + breakdown |
| GET    | `/seasons`         | No   | List all seasons (paginated)            |
| GET    | `/seasons/current` | No   | Current active season                   |

#### `GET /leaderboard`

```python
Query params: page (default 1), page_size (default 20, max leaderboard_size)
1. Join player_net_worth with players (exclude is_ai=True)
2. Order by score_micro DESC
3. Paginate
4. Compute rank using offset: rank = (page-1)*page_size + index + 1
5. Return LeaderboardResponse
```

#### `GET /leaderboard/me`

```python
1. Load player_net_worth for current player
2. If not found: return rank=None with zeros
3. Compute rank via subquery: COUNT(*) WHERE score_micro > my_score (among non-AI)
4. Return MyRankResponse
```

#### `GET /seasons`

```python
Query params: page, page_size
1. Query seasons ordered by season_number DESC
2. Paginate
```

#### `GET /seasons/current`

```python
1. Query season WHERE status = ACTIVE
2. If none: return 404
3. Return SeasonResponse
```

Register router in `main.py`.

---

## Step 8 — Tests

### `test_leaderboard.py` (🆕 new file)

#### Net Worth Computation

| Test                                              | Assertion                               |
| ------------------------------------------------- | --------------------------------------- |
| Balance-only player has correct net worth         | net_worth = balance, portfolio = 0      |
| Player with gate shares at market price           | portfolio includes share × market_price |
| Player with gate shares uses fundamental fallback | portfolio computed from yield/stability |
| Player with guild shares                          | portfolio includes guild share value    |
| Collapsed gate shares excluded from portfolio     | net_worth ignores COLLAPSED gates       |

#### Decay

| Test                           | Assertion                 |
| ------------------------------ | ------------------------- |
| Active player: no decay        | score = net_worth         |
| Inactive player: decay applied | score < net_worth         |
| Decay floors at minimum        | score ≥ net_worth × floor |

#### Season Management

| Test                                       | Assertion                               |
| ------------------------------------------ | --------------------------------------- |
| First season created automatically         | Season record exists after check_season |
| Season completes when duration exceeded    | Status → COMPLETED, end_tick set        |
| Season results recorded with correct ranks | SeasonResult rows match score order     |
| New season starts after completion         | New ACTIVE season, incremented number   |

#### API

| Test                                   | Assertion                          |
| -------------------------------------- | ---------------------------------- |
| Leaderboard returns paginated rankings | Correct order, pagination metadata |
| Leaderboard excludes AI players        | AI bots not in response            |
| Leaderboard /me returns player's rank  | Correct rank and breakdown         |
| Seasons list returns seasons           | Correct data                       |
| Current season returns active season   | Status = ACTIVE                    |

#### Integration

| Test                            | Assertion                            |
| ------------------------------- | ------------------------------------ |
| Full tick with leaderboard runs | execute_tick completes without error |

### Estimated: ~18 tests

---

## Execution Order

```
Step 1:  Config additions                → config.py (edit)
Step 2:  Migration                       → migration (new)
Step 3:  Models                          → models/leaderboard.py (new), models/__init__.py (edit)
Step 4:  Leaderboard service             → services/leaderboard.py (new)
Step 5:  Pipeline wiring                 → simulation/tick.py (edit)
Step 6:  State hash extension            → simulation/state_hash.py (edit)
Step 7:  API + schemas                   → api/leaderboard.py (new), schemas/leaderboard.py (new), main.py (edit)
Step 8:  Tests                           → tests/test_leaderboard.py (new)
```

### Estimated: ~4 new files, ~4 modified files, ~18 new tests

---

## Key Design Decisions

| Decision                                    | Rationale                                                      |
| ------------------------------------------- | -------------------------------------------------------------- |
| Net worth = balance + portfolio value       | Escrow already deducted from balance; conservative estimate    |
| Score decay based on activity, not time     | Rewards active participation, not just holding                 |
| Decay grace period (100 ticks)              | Short breaks don't penalize; extended absence does             |
| Decay floor at 50%                          | Prevents total score wipeout for returning players             |
| Update every N ticks (not every tick)       | Performance: batch computation is expensive with many players  |
| Season check every tick, update every N     | Season transitions are time-critical; net worth updates aren't |
| No rewards this phase                       | Keeps it simple; rewards would require new faucet/entry type   |
| AI players excluded from leaderboard API    | AI is infrastructure, not competition                          |
| AI included in net worth computation        | Maintains data completeness; filtered at API layer             |
| Reuse \_share_value_micro from anti_exploit | Same valuation logic; avoid duplication                        |
| Composite PK on season_results              | One result per player per season, clean constraint             |
| Rank computed at query time for leaderboard | Avoids recomputing all ranks on every score change             |
| Rank stored in season_results               | Frozen at season end; historical accuracy                      |

---

## Edge Cases

| Edge Case                                | Expected Behavior                                              |
| ---------------------------------------- | -------------------------------------------------------------- |
| Player with no holdings or trades        | net_worth = balance, score = balance, last_active = 0          |
| Player with 0 balance and 0 holdings     | net_worth = 0, score = 0                                       |
| Gate with no market price                | Fundamental fallback used for valuation                        |
| Guild share with no market price         | Fallback: guild_creation_cost // total_shares                  |
| Player registered mid-season             | Appears on leaderboard at next update cycle                    |
| Tick not divisible by update interval    | Leaderboard skipped, season still checked                      |
| Season ends exactly on update interval   | Season finalization forces leaderboard update                  |
| Season end with 0 non-AI players         | No season_results rows, season still marked COMPLETED          |
| Very long inactivity (1000+ ticks)       | Decay floors at 50% — score never goes below half of net worth |
| Player at exactly grace period boundary  | No decay (> not >=)                                            |
| Multiple seasons complete simultaneously | Not possible — checked every tick, max 1 transition per tick   |

---

## Dependencies

- Phase 2: Player model, balance
- Phase 4: Gates, gate shares
- Phase 5: Market prices, orders (for activity detection)
- Phase 6: Guilds, guild shares
- Phase 9: `_share_value_micro` reused for portfolio valuation

---

## Guidelines for Responses

1. **Small changes:** If a file only needs a minor update, just tell me _what_ to change and _where_.

2. **Label every file output:** Always specify whether the file is being:
   - 🆕 **Created** (new file)
   - ✏️ **Updated** (partial change)
   - 🔁 **Replaced** (full rewrite)

3. **Go step by step:**
   - If a step involves **fewer than 2 files**, combine it with the next.
   - Aim for **2–3 steps** at a time.

4. **No overthinking:** Don't spiral into deep analysis.
