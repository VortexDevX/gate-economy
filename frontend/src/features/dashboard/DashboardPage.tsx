import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Aperture,
  ArrowLeftRight,
  ArrowRight,
  Coins,
  Compass,
  Gem,
  Hourglass,
  Radio,
  ScrollText,
  Shield,
  Sparkles,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import type { MarketAssetResponse } from "../../api/types";
import { GameAction, GameEmpty, RankCrest, StabilityMeter } from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import {
  useMarketOverview,
  useMyIntents,
  useMyOrders,
  useMyPortfolio,
  useNews,
  useSimulationStatus,
} from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency, formatCurrencyCompact } from "../../utils/format";

type Objective = {
  eyebrow: string;
  title: string;
  copy: string;
  action: string;
  to: string;
  tone: "gold" | "aether" | "danger" | "violet";
};

export default function DashboardPage() {
  const player = useAuthStore((state) => state.player);
  const portfolioQuery = useMyPortfolio();
  const marketQuery = useMarketOverview({ sort_by: "YIELD", limit: 6 });
  const { data: simulation } = useSimulationStatus();
  const { data: intents } = useMyIntents({ limit: 6 });
  const { data: orders } = useMyOrders({ limit: 6 });
  const { data: news } = useNews({ limit: 5 });

  const portfolio = portfolioQuery.data;
  const market = marketQuery.data;
  const pendingIntents = intents?.items.filter((item) => item.status === "QUEUED" || item.status === "PROCESSING") ?? [];
  const openOrders = orders?.orders.filter((order) => order.status === "OPEN" || order.status === "PARTIAL") ?? [];
  const positions = portfolio?.gate_positions ?? [];
  const worldLive = Boolean(simulation?.is_running && !simulation?.is_paused);
  const objective = getObjective({ worldLive, pendingIntents: pendingIntents.length, positions });
  const bestGates = market?.items.filter((gate) => gate.status !== "COLLAPSED").slice(0, 3) ?? [];
  const dangerousPositions = positions.filter((position) => position.risk_band === "CRITICAL" || position.risk_band === "WATCH");
  const questProgress = positions.length > 0 ? 2 : pendingIntents.length > 0 ? 1 : 0;
  const pendingCount = pendingIntents.length + openOrders.length;

  return (
    <div className="sanctum-page">
      <section className="sanctum-hero" aria-labelledby="sanctum-title">
        <div className="sanctum-hero-art" aria-hidden="true" />
        <div className="sanctum-hero-vignette" aria-hidden="true" />
        <span className="sanctum-spark spark-a" aria-hidden="true" />
        <span className="sanctum-spark spark-b" aria-hidden="true" />
        <span className="sanctum-spark spark-c" aria-hidden="true" />

        <header className="sanctum-title-block">
          <span className="sanctum-kicker"><Aperture size={15} aria-hidden="true" /> Hunter sanctum · Cycle {simulation?.current_tick ?? 0}</span>
          <h1 id="sanctum-title">What will you risk, <em>{player?.username ?? "Hunter"}?</em></h1>
          <p>Discover living gates. Own their power. Leave before they collapse.</p>
        </header>

        <article className={`sanctum-mission mission-${objective.tone}`}>
          <div className="mission-topline">
            <span><Compass size={16} aria-hidden="true" /> Active mission</span>
            <strong>{questProgress}/4</strong>
          </div>
          <div
            className="mission-progress"
            role="progressbar"
            aria-label="Initiation progress"
            aria-valuemin={0}
            aria-valuemax={4}
            aria-valuenow={questProgress}
          ><i style={{ width: `${questProgress * 25}%` }} /></div>
          <span className="mission-eyebrow">{objective.eyebrow}</span>
          <h2>{objective.title}</h2>
          <p>{objective.copy}</p>
          <GameAction to={objective.to}>{objective.action}</GameAction>
          {!worldLive && (
            <div className="mission-warning"><AlertTriangle size={15} aria-hidden="true" /> Realm paused. Commands remain safe.</div>
          )}
        </article>

        <div className="portal-whisper" aria-hidden="true">
          <span /><strong>{worldLive ? "THE GATE IS LISTENING" : "THE GATE SLEEPS"}</strong><span />
        </div>

        <aside className="sanctum-status" aria-label="Hunter status">
          <div className="sanctum-status-head">
            <span>Hunter status</span>
            <strong>{positions.length} gates</strong>
          </div>
          <StatusShard
            icon={<WalletCards />}
            label="Coin ready"
            value={`¤ ${formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}`}
            tone="gold"
          />
          <StatusShard
            icon={<TrendingUp />}
            label="Cycle income"
            value={`+¤ ${formatCurrency(portfolio?.projected_yield_per_tick_micro ?? 0)}`}
            tone="good"
          />
          <StatusShard
            icon={<Hourglass />}
            label="Commands"
            value={pendingCount ? String(pendingCount).padStart(2, "0") : "Clear"}
            tone={pendingCount ? "aether" : "muted"}
          />
          <StatusShard
            icon={<Shield />}
            label="Exposure"
            value={dangerousPositions.length ? `${dangerousPositions.length} at risk` : "Stable"}
            tone={dangerousPositions.length ? "danger" : "good"}
          />
          <Link to="/profile" className="sanctum-status-link">Open hunter vault <ArrowRight size={15} /></Link>
        </aside>

        <nav className="sanctum-actions" aria-label="Choose your next move">
          <ActionTile to="/discover" icon={<Sparkles />} label="Scout" detail="Find a new gate" tone="violet" hot={positions.length === 0} />
          <ActionTile to="/gates" icon={<ArrowLeftRight />} label="Trade" detail="Enter gate market" tone="aether" />
          <ActionTile to="/profile" icon={<Gem />} label="Holdings" detail="Guard your wealth" tone="gold" />
          <ActionTile to="/orders" icon={<ScrollText />} label="Commands" detail="Track every move" tone="ember" badge={pendingCount} />
        </nav>
      </section>

      <main className="sanctum-below">
        {portfolioQuery.error && <ErrorAlert message="Hunter vault could not be read. Gate market remains available." />}

        <section className="sanctum-market" aria-labelledby="market-watch-title">
          <header className="sanctum-section-head">
            <div><span><Radio size={14} /> Live gate signal</span><h2 id="market-watch-title">Market watch</h2><p>Cost. Yield. Collapse risk. Nothing else matters.</p></div>
            <Link to="/gates">Open full market <ArrowRight size={16} /></Link>
          </header>
          {marketQuery.isLoading && <LoadingSpinner />}
          {marketQuery.error && <ErrorAlert message="Gate market is unavailable right now." />}
          {!marketQuery.isLoading && !marketQuery.error && bestGates.length === 0 && (
            <GameEmpty title="No gates in this realm" message="Fund an expedition and create the first tradeable dungeon asset." action={{ to: "/discover", label: "Create first gate" }} />
          )}
          {bestGates.length > 0 && <div className="sanctum-gate-grid">{bestGates.map((gate) => <GateWatchCard key={gate.asset_id} gate={gate} />)}</div>}
        </section>

        <section className="sanctum-dispatches" aria-labelledby="realm-signals-title">
          <header className="sanctum-section-head">
            <div><span><Activity size={14} /> Realm intelligence</span><h2 id="realm-signals-title">Signals from beyond</h2><p>Events can change income and survival odds.</p></div>
            <Link to="/news">All dispatches <ArrowRight size={16} /></Link>
          </header>
          {!news?.items.length ? (
            <div className="dispatch-silence"><Radio size={26} /><div><strong>No signal yet</strong><span>{worldLive ? "Realm is waking. First reports arrive after world events." : "Time is frozen. No new omens can form."}</span></div></div>
          ) : (
            <div className="sanctum-dispatch-list">
              {news.items.slice(0, 4).map((item, index) => (
                <article key={item.id}>
                  <span className="dispatch-index">0{index + 1}</span>
                  <div><small>{plainCategory(item.category)}</small><h3>{item.headline}</h3></div>
                  <span
                    className={`dispatch-heat heat-${Math.min(5, Math.max(1, item.importance))}`}
                    role="img"
                    aria-label={`Importance ${item.importance} of 5`}
                  />
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function StatusShard({ icon, label, value, tone }: { icon: React.ReactElement; label: string; value: string; tone: string }) {
  return <div className={`status-shard shard-${tone}`}><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>;
}

function ActionTile({ to, icon, label, detail, tone, hot = false, badge = 0 }: { to: string; icon: React.ReactElement; label: string; detail: string; tone: string; hot?: boolean; badge?: number }) {
  return (
    <Link to={to} className={`sanctum-action action-${tone} ${hot ? "is-hot" : ""}`}>
      <span className="sanctum-action-icon">{icon}</span>
      <span><strong>{label}</strong><small>{detail}</small></span>
      {hot && <i>Start here</i>}
      {!hot && badge > 0 && <i>{badge}</i>}
      <ArrowRight size={17} aria-hidden="true" />
    </Link>
  );
}

function GateWatchCard({ gate }: { gate: MarketAssetResponse }) {
  return (
    <Link to={`/gates/${gate.asset_id}`} className={`gate-watch-card watch-${gate.risk_band.toLowerCase()}`}>
      <div className="gate-watch-visual"><span className="gate-orbit" aria-hidden="true" /><RankCrest rank={gate.rank} size="lg" /><small>{gate.ticker}</small></div>
      <div className="gate-watch-copy">
        <div><span>{plainRisk(gate.risk_band)}</span><h3>{gate.display_name}</h3></div>
        <StabilityMeter value={gate.stability} threshold={gate.collapse_threshold} compact />
        <div className="gate-watch-numbers">
          <span><small>One share</small><strong>¤ {formatCurrency(gate.mark_price_micro)}</strong></span>
          <span><small>Cycle yield</small><strong>+¤ {formatCurrency(gate.yield_per_share_micro)}</strong></span>
          <span><small>Volume</small><strong>¤ {formatCurrencyCompact(gate.volume_24h_micro)}</strong></span>
        </div>
      </div>
      <ArrowRight className="gate-watch-arrow" size={18} aria-hidden="true" />
    </Link>
  );
}

function getObjective({ worldLive, pendingIntents, positions }: { worldLive: boolean; pendingIntents: number; positions: Array<{ risk_band: string; gate_id: string }> }): Objective {
  if (!worldLive) return { eyebrow: "World engine offline", title: "Wake the realm", copy: "Explore rules and prepare your strategy while time is frozen.", action: "Open field guide", to: "/guide", tone: "danger" };
  if (pendingIntents > 0) return { eyebrow: `${pendingIntents} command${pendingIntents === 1 ? "" : "s"} awaiting cycle`, title: "Your move is in motion", copy: "World cycles decide execution. Watch result before committing more coin.", action: "Watch command queue", to: "/orders", tone: "aether" };
  const critical = positions.find((position) => position.risk_band === "CRITICAL");
  if (critical) return { eyebrow: "Collapse warning", title: "A holding is dying", copy: "Critical stability means permanent loss is near. Inspect gate and choose your exit.", action: "Protect the position", to: `/gates/${critical.gate_id}`, tone: "danger" };
  if (positions.length === 0) return { eyebrow: "First contract", title: "Open your first gate", copy: "Scout E-rank for ¤0.10. Success creates a new market asset and grants your finder stake.", action: "Launch expedition", to: "/discover", tone: "violet" };
  return { eyebrow: "Portfolio awakened", title: "Turn danger into income", copy: "Compare gate yield against stability. Grow carefully, then escape before collapse.", action: "Inspect holdings", to: "/profile", tone: "gold" };
}

function plainRisk(risk: string): string {
  const labels: Record<string, string> = { STABLE: "Stable gate", WATCH: "Unstable", CRITICAL: "Collapse near", OFFERING: "Awakening", COLLAPSED: "Lost forever" };
  return labels[risk] ?? risk.replace(/_/g, " ").toLowerCase();
}

function plainCategory(category: string): string {
  const labels: Record<string, string> = { EVENT: "World omen", GATE: "Gate report", MARKET: "Market move", GUILD: "Guild report", LEADERBOARD: "Season report", WORLD: "Realm dispatch" };
  return labels[category] ?? category.replace(/_/g, " ").toLowerCase();
}
