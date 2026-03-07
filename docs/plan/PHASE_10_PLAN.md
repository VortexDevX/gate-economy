# PHASE 10 PLAN: Leaderboards & Seasons

## Goal
Rank players by net worth in seasonal competition with inactivity decay and historical results.

## Canonical Scope (Aligned with `docs/plan/PLAN.md`)

### Data Model
- `seasons`
  - `id`, `name`, `started_at_tick`, `ends_at_tick`, `status`
- `leaderboard_entries`
  - `season_id`, `player_id`, `net_worth_micro`, `score`, `rank`, `last_active_tick`, `updated_at_tick`
- `season_results`
  - `season_id`, `player_id`, `final_rank`, `final_score`

### Net Worth
- `balance + gate holdings value + guild holdings value`
- Updated every configured interval (default every 12 ticks).

### Decay
- Inactive players decay by configured decay factor after inactivity threshold.

### Season Lifecycle
1. Active season runs and leaderboard updates continuously.
2. On season end, snapshot standings into `season_results`.
3. Mark season completed.
4. Start new active season.
5. Economy state persists; only rankings reset.

### APIs
- `GET /leaderboard`
- `GET /leaderboard/me`
- `GET /seasons`
- `GET /seasons/{id}/results`

## Acceptance Criteria
- Net worth ranking is correct.
- Inactivity decay affects ordering.
- AI players excluded from public leaderboard.
- Season snapshots are correct and immutable.
- No new faucet introduced by leaderboard/season logic.

## Implementation Notes (Current Repo)
- Public API includes `GET /seasons/{season_id}/results` and `GET /leaderboard/me`.
- Current storage uses `player_net_worth` as the live leaderboard state table.
- Follow-up migration task: rename `player_net_worth` to canonical `leaderboard_entries` (or add compatibility view) to match naming in main plan exactly.
