import { useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, Coins, Filter, RefreshCw, Sparkles, TrendingUp } from "lucide-react";
import type { MarketOverviewParams } from "../../api/market";
import type { MarketAssetResponse } from "../../api/types";
import {
  GameAction,
  GameEmpty,
  GamePanel,
  RankCrest,
  ScreenHeader,
  StabilityMeter,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import Pagination from "../../components/Pagination";
import { useMarketOverview } from "../../hooks/queries";
import { formatCurrency, formatCurrencyCompact } from "../../utils/format";

const STATUSES = ["", "OFFERING", "ACTIVE", "UNSTABLE", "COLLAPSED"] as const;
const RANKS = ["", "E", "D", "C", "B", "A", "S", "S_PLUS"] as const;
const SORT_OPTIONS: Array<{ value: NonNullable<MarketOverviewParams["sort_by"]>; label: string }> = [
  { value: "YIELD", label: "Best income first" },
  { value: "RISK", label: "Most dangerous first" },
  { value: "VOLUME", label: "Most traded first" },
  { value: "NEWEST", label: "Newest discoveries" },
];
const PAGE_SIZE = 12;

export default function GatesListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [rankFilter, setRankFilter] = useState("");
  const [sortBy, setSortBy] = useState<NonNullable<MarketOverviewParams["sort_by"]>>("YIELD");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const { data, isLoading, error, isFetching } = useMarketOverview({
    status: statusFilter || undefined,
    rank: rankFilter || undefined,
    sort_by: sortBy,
    offset,
    limit: PAGE_SIZE,
  });
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const resetFilters = () => {
    setStatusFilter("");
    setRankFilter("");
    setSortBy("YIELD");
    setPage(1);
  };

  return (
    <div className="game-page atlas-page">
      <ScreenHeader
        eyebrow="Gate Atlas · Live instruments"
        title="Choose a gate worth the danger"
        description="Start with the card, not the spreadsheet: see what one share costs, what it can earn each cycle, and how close the gate is to collapse."
        action={<GameAction to="/discover"><Sparkles size={17} /> Discover a new gate</GameAction>}
      />

      {data && (
        <section className="atlas-state-strip" aria-label="Gate states">
          <AtlasCount label="Earning now" value={data.active_count} tone="good" />
          <AtlasCount label="Preparing" value={data.offering_count} tone="aether" />
          <AtlasCount label="In danger" value={data.unstable_count} tone="warn" />
          <AtlasCount label="Lost forever" value={data.collapsed_count} tone="danger" />
        </section>
      )}

      <GamePanel className="atlas-filters" accent="muted">
        <div className="atlas-filter-title"><Filter size={17} aria-hidden="true" /><span>Shape the atlas</span></div>
        <FilterSelect label="Gate state" value={statusFilter} onChange={(value) => { setStatusFilter(value); setPage(1); }}>
          {STATUSES.map((status) => <option key={status} value={status}>{status ? plainStatus(status) : "Every state"}</option>)}
        </FilterSelect>
        <FilterSelect label="Minimum rank" value={rankFilter} onChange={(value) => { setRankFilter(value); setPage(1); }}>
          {RANKS.map((rank) => <option key={rank} value={rank}>{rank ? `Rank ${rank === "S_PLUS" ? "S+" : rank}` : "Every rank"}</option>)}
        </FilterSelect>
        <FilterSelect label="Show me" value={sortBy} onChange={(value) => { setSortBy(value as NonNullable<MarketOverviewParams["sort_by"]>); setPage(1); }}>
          {SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </FilterSelect>
        <div className="atlas-filter-count">
          {isFetching && !isLoading && <RefreshCw size={14} className="animate-spin" aria-hidden="true" />}
          <strong>{data?.total ?? 0}</strong><span>gates found</span>
        </div>
      </GamePanel>

      {isLoading && <LoadingSpinner className="py-24" />}
      {error && <ErrorAlert message="The Gate Atlas could not reach the market feed." />}
      {data && data.items.length === 0 && (
        <GameEmpty
          title={data.total === 0 && !statusFilter && !rankFilter ? "No gates exist in this world yet" : "Nothing matches these filters"}
          message={data.total === 0 && !statusFilter && !rankFilter ? "Launch an expedition to create the first gate and receive a finder stake." : "Clear the filters or choose a broader rank and state."}
          action={data.total === 0 && !statusFilter && !rankFilter ? { to: "/discover", label: "Create the first gate" } : undefined}
        />
      )}
      {data && data.items.length === 0 && (statusFilter || rankFilter) && (
        <button className="game-button game-button-ghost mx-auto" onClick={resetFilters}>Reset atlas filters</button>
      )}

      {data && data.items.length > 0 && (
        <div className="atlas-card-grid">
          {data.items.map((gate) => <AtlasGateCard key={gate.asset_id} gate={gate} />)}
        </div>
      )}

      {totalPages > 1 && <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />}
    </div>
  );
}

function AtlasGateCard({ gate }: { gate: MarketAssetResponse }) {
  const collapsed = gate.status === "COLLAPSED";
  return (
    <article className={`atlas-gate-card atlas-gate-${gate.status.toLowerCase()}`}>
      <div className="atlas-gate-visual" aria-hidden="true">
        <span className="atlas-gate-ring atlas-gate-ring-one" />
        <span className="atlas-gate-ring atlas-gate-ring-two" />
        <RankCrest rank={gate.rank} size="lg" />
      </div>
      <div className="atlas-gate-main">
        <div className="atlas-gate-heading">
          <div><span>{gate.ticker}</span><h2>{gate.display_name}</h2></div>
          <span className={`gate-state gate-state-${gate.status.toLowerCase()}`}>{plainStatus(gate.status)}</span>
        </div>

        <StabilityMeter value={gate.stability} threshold={gate.collapse_threshold} compact />

        <div className="atlas-gate-facts">
          <div><Coins size={15} /><span>One share</span><strong>{collapsed ? "Worthless" : `¤ ${formatCurrency(gate.mark_price_micro)}`}</strong></div>
          <div><TrendingUp size={15} /><span>Earns / cycle</span><strong className={gate.status === "ACTIVE" ? "tone-good" : ""}>{gate.status === "ACTIVE" ? `+¤ ${formatCurrency(gate.yield_per_share_micro)}` : "Not earning"}</strong></div>
          <div><Activity size={15} /><span>Market activity</span><strong>¤ {formatCurrencyCompact(gate.volume_24h_micro)}</strong></div>
        </div>

        <div className="atlas-gate-advice">{gateAdvice(gate)}</div>
        <Link to={`/gates/${gate.asset_id}`} className="atlas-gate-open">
          {collapsed ? "Read gate record" : "Enter gate chamber"}<ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

function FilterSelect({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return <label className="atlas-filter-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{children}</select></label>;
}

function AtlasCount({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className={`atlas-count atlas-count-${tone}`}><strong>{value}</strong><span>{label}</span></div>;
}

function plainStatus(status: string): string {
  const labels: Record<string, string> = { OFFERING: "Preparing", ACTIVE: "Earning", UNSTABLE: "In danger", COLLAPSED: "Collapsed" };
  return labels[status] ?? status.replace(/_/g, " ").toLowerCase();
}

function gateAdvice(gate: MarketAssetResponse): string {
  if (gate.status === "COLLAPSED") return "This gate is permanently closed. Its shares no longer have value.";
  if (gate.status === "OFFERING") return "A new gate. Shares can trade, but income begins only after activation.";
  if (gate.status === "UNSTABLE" || gate.risk_band === "CRITICAL") return "Danger zone. Yield has stopped and collapse may erase the remaining value.";
  if (gate.risk_band === "WATCH") return "Income is flowing, but the safety buffer is narrowing. Plan an exit.";
  return "Stable enough to produce income now. Compare price against yield before buying.";
}
