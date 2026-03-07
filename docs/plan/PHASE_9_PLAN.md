# PHASE 9 PLAN: Anti-Exploit & Economic Balance

## Goal
Add anti-dominance friction and safety controls so no single strategy can permanently dominate.

## Canonical Scope (Aligned with `docs/plan/PLAN.md`)

### Mechanisms
- **Ownership Concentration Penalty (yield-side):**
  - Yield payout effectiveness by ownership band:
  - `<=25%: 100%`, `>50%: 80%`, `>75%: 60%`, `>90%: 30%`
  - Unpaid portion remains in treasury.
- **Liquidity Decay:**
  - Holdings inactive for more than threshold ticks incur per-tick cost.
- **Float Control Cap:**
  - Max single-player ownership per asset: **80%**.
  - Enforced at **matching time**.
- **Portfolio Maintenance:**
  - High net worth accounts pay progressive maintenance sink.
- **Progressive Fees tuning:**
  - Fee parameters remain tunable via simulation parameters.

### Tick Pipeline Integration
- Run anti-exploit maintenance after market/event steps and before finalizing tick.
- All costs and transfers remain ledgered and conservation-safe.

### Data Requirements
- Holding recency must be trackable (`last_trade_tick` or equivalent market activity marker).
- Market prices are required for maintenance/decay valuation.

## Acceptance Criteria
- Concentrated holders receive reduced effective yield.
- Illiquid holdings are charged after inactivity threshold.
- Trades that would exceed 80% are blocked at matching time.
- High-net-worth maintenance is measurable and ledgered.
- Whale simulation shows diminishing returns.
- Conservation invariant remains true.

## Implementation Notes (Current Repo)
- Float cap is now enforced at matching time (not intent validation) with default `max_player_ownership_pct = 0.80`.
- Existing anti-exploit includes sink charges for maintenance/concentration/liquidity and is fully tested.
- Follow-up task: migrate concentration handling from sink-charge model to pure yield-side reduction model for strict canonical parity.
