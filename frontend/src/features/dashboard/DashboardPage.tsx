import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Coins,
  Compass,
  Hourglass,
  Radio,
  ScrollText,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import type { MarketAssetResponse } from "../../api/types";
import {
  GameAction,
  GameEmpty,
  GamePanel,
  PanelHeading,
  RankCrest,
  ScreenHeader,
  StabilityMeter,
  StatRune,
} from "../../components/game/GameUI";
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
  const questProgress: number = positions.length > 0 ? 2 : pendingIntents.length > 0 ? 1 : 0;

  return (
    <div className="game-page command-page">
      <ScreenHeader
        eyebrow={`Cycle ${simulation?.current_tick ?? 0} · ${worldLive ? "world in motion" : "world dormant"}`}
        title={`Welcome back, ${player?.username ?? "Hunter"}`}
        description="This is your command chamber. Follow the active contract, grow a gate portfolio, and get out before unstable gates collapse."
        action={<GameAction to="/guide" tone="ghost">Open field guide</GameAction>}
      />

      {portfolioQuery.error && <ErrorAlert message="Your portfolio could not be read. The market and world feed are still available." />}

      <section className="command-grid">
        <GamePanel className="objective-card" accent={objective.tone}>
          <div className="objective-copy">
            <div className="objective-label"><Compass size={16} aria-hidden="true" /> Active contract</div>
            <span className="objective-eyebrow">{objective.eyebrow}</span>
            <h2>{objective.title}</h2>
            <p>{objective.copy}</p>
            <GameAction to={objective.to}>{objective.action}</GameAction>
            {!worldLive && (
              <div className="objective-operator-note">
                <AlertTriangle size={15} aria-hidden="true" />
                Operator action required. Queued commands remain safe until the world resumes.
              </div>
            )}
          </div>
          <div className={`objective-portal portal-${objective.tone}`} aria-hidden="true">
            <span className="portal-ring portal-ring-one" />
            <span className="portal-ring portal-ring-two" />
            <span className="portal-core"><Sparkles size={34} /></span>
            <span className="portal-particle portal-particle-a" />
            <span className="portal-particle portal-particle-b" />
            <span className="portal-particle portal-particle-c" />
          </div>
        </GamePanel>

        <GamePanel className="quest-card" accent="violet">
          <div className="quest-card-top">
            <div>
              <span className="game-eyebrow">Initiation path</span>
              <h2>Become a Gate Baron</h2>
            </div>
            <span className="quest-progress-number">{questProgress}/4</span>
          </div>
          <div className="quest-progress-track"><span style={{ width: `${questProgress * 25}%` }} /></div>
          <ol className="quest-steps">
            <QuestStep number="01" title="Scout a gate" copy="Pay for an expedition and receive a finder stake." active={questProgress === 0} complete={questProgress > 0} />
            <QuestStep number="02" title="Survive offering" copy="The gate must activate before it starts producing yield." active={questProgress === 1} complete={questProgress > 1} />
            <QuestStep number="03" title="Earn each cycle" copy="Active shares pay coin while the gate remains stable." active={questProgress === 2} complete={questProgress > 2} />
            <QuestStep number="04" title="Exit before collapse" copy="Trade or rebalance when stability turns dangerous." active={questProgress === 3} complete={questProgress > 3} />
          </ol>
        </GamePanel>
      </section>

      <section className="command-stats" aria-label="Your economy at a glance">
        <StatRune
          label="Coin ready"
          value={`¤ ${formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}`}
          note={portfolio?.reserved_cash_micro ? `¤ ${formatCurrency(portfolio.reserved_cash_micro)} committed to orders` : "Available for expeditions and trades"}
          tone="gold"
          icon={<WalletCards size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Income each cycle"
          value={`+¤ ${formatCurrency(portfolio?.projected_yield_per_tick_micro ?? 0)}`}
          note={positions.length ? `Produced by ${positions.length} gate position${positions.length === 1 ? "" : "s"}` : "Own an active gate to begin earning"}
          tone="good"
          icon={<TrendingUp size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Actions waiting"
          value={String(pendingIntents.length + openOrders.length)}
          note={worldLive ? "Resolve as the world advances" : "Frozen until the world engine returns"}
          tone={pendingIntents.length + openOrders.length ? "aether" : "muted"}
          icon={<Hourglass size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Dangerous exposure"
          value={dangerousPositions.length ? String(dangerousPositions.length) : "None"}
          note={dangerousPositions.length ? "Review before the next collapse check" : "No holdings are inside the danger corridor"}
          tone={dangerousPositions.length ? "danger" : "good"}
          icon={<ShieldCheck size={18} aria-hidden="true" />}
        />
      </section>

      <section className="command-content-grid">
        <GamePanel className="market-preview" accent="aether">
          <PanelHeading
            title="Gates worth inspecting"
            detail="Each card answers three questions: cost, income, and danger."
            action={<Link to="/gates" className="panel-text-link">Open the full atlas <ArrowRight size={15} /></Link>}
          />
          {marketQuery.isLoading && <LoadingSpinner />}
          {marketQuery.error && <ErrorAlert message="The gate atlas is unavailable right now." />}
          {!marketQuery.isLoading && !marketQuery.error && bestGates.length === 0 && (
            <GameEmpty
              title="The atlas is blank"
              message="No gates exist yet. Your first expedition can create the first tradeable asset in this world."
              action={{ to: "/discover", label: "Scout the first gate" }}
            />
          )}
          {bestGates.length > 0 && (
            <div className="gate-preview-grid">
              {bestGates.map((gate) => <GatePreviewCard key={gate.asset_id} gate={gate} />)}
            </div>
          )}
        </GamePanel>

        <GamePanel className="world-pulse-card" accent="gold">
          <PanelHeading title="World pulse" detail="Signals that can change what your gates earn or how long they survive." />
          {!news?.items.length ? (
            <GameEmpty
              title="No dispatches yet"
              message={worldLive ? "The first headlines will appear as cycles create market and gate events." : "The world is dormant, so there are no events to report."}
            />
          ) : (
            <div className="dispatch-list">
              {news.items.slice(0, 4).map((item) => (
                <article key={item.id} className="dispatch-item">
                  <span className={`dispatch-rank dispatch-rank-${Math.min(5, Math.max(1, item.importance))}`} aria-label={`Importance ${item.importance} of 5`} />
                  <div>
                    <span>{plainCategory(item.category)}</span>
                    <h3>{item.headline}</h3>
                  </div>
                </article>
              ))}
              <Link to="/news" className="panel-text-link">Read all dispatches <ArrowRight size={15} /></Link>
            </div>
          )}
        </GamePanel>
      </section>

      <GamePanel className="game-loop-card" accent="muted">
        <PanelHeading title="The whole game in four moves" detail="You are trading expiring magical assets—not fighting inside the dungeon." />
        <div className="game-loop">
          <LoopMove icon={<Compass />} number="1" title="Discover" copy="Fund an expedition. Higher ranks cost more and are rarer." />
          <LoopMove icon={<Coins />} number="2" title="Own" copy="Keep the finder stake or buy shares from the live market." />
          <LoopMove icon={<Activity />} number="3" title="Earn" copy="Active gates pay yield every world cycle while stable." />
          <LoopMove icon={<AlertTriangle />} number="4" title="Escape" copy="Sell or rebalance before instability becomes collapse." />
        </div>
      </GamePanel>
    </div>
  );
}

function QuestStep({ number, title, copy, active, complete }: { number: string; title: string; copy: string; active: boolean; complete: boolean }) {
  return (
    <li className={`${active ? "is-active" : ""} ${complete ? "is-complete" : ""}`}>
      <span>{complete ? "✓" : number}</span>
      <div><strong>{title}</strong><p>{copy}</p></div>
    </li>
  );
}

function GatePreviewCard({ gate }: { gate: MarketAssetResponse }) {
  return (
    <Link to={`/gates/${gate.asset_id}`} className="gate-preview-card">
      <div className="gate-preview-top">
        <RankCrest rank={gate.rank} />
        <div className="min-w-0">
          <span>{gate.ticker}</span>
          <h3>{gate.display_name}</h3>
        </div>
        <span className={`risk-word risk-${gate.risk_band.toLowerCase()}`}>{plainRisk(gate.risk_band)}</span>
      </div>
      <StabilityMeter value={gate.stability} threshold={gate.collapse_threshold} compact />
      <div className="gate-preview-economy">
        <div><span>Share price</span><strong>¤ {formatCurrency(gate.mark_price_micro)}</strong></div>
        <div><span>Income / share</span><strong className="tone-good">+¤ {formatCurrency(gate.yield_per_share_micro)}</strong></div>
        <div><span>Trade volume</span><strong>¤ {formatCurrencyCompact(gate.volume_24h_micro)}</strong></div>
      </div>
      <span className="gate-preview-open">Inspect gate <ArrowRight size={15} /></span>
    </Link>
  );
}

function LoopMove({ icon, number, title, copy }: { icon: React.ReactElement; number: string; title: string; copy: string }) {
  return (
    <article className="loop-move">
      <div className="loop-move-icon">{icon}<span>{number}</span></div>
      <div><h3>{title}</h3><p>{copy}</p></div>
    </article>
  );
}

function getObjective({ worldLive, pendingIntents, positions }: { worldLive: boolean; pendingIntents: number; positions: Array<{ risk_band: string; gate_id: string }> }): Objective {
  if (!worldLive) {
    return {
      eyebrow: "World engine offline",
      title: "Time is frozen beyond the gate",
      copy: "You can inspect the economy, but expeditions and orders will not resolve until the simulation worker is running.",
      action: "Learn the game while you wait",
      to: "/guide",
      tone: "danger",
    };
  }
  if (pendingIntents > 0) {
    return {
      eyebrow: `${pendingIntents} action${pendingIntents === 1 ? "" : "s"} awaiting the next cycle`,
      title: "Your command has entered the world",
      copy: "Actions resolve on world cycles, not instantly. Watch the action queue for execution or rejection.",
      action: "Watch action queue",
      to: "/orders",
      tone: "aether",
    };
  }
  const critical = positions.find((position) => position.risk_band === "CRITICAL");
  if (critical) {
    return {
      eyebrow: "Collapse warning",
      title: "One of your holdings is in danger",
      copy: "Critical stability means the gate is close to permanent collapse. Inspect the position and consider an exit.",
      action: "Protect the position",
      to: `/gates/${critical.gate_id}`,
      tone: "danger",
    };
  }
  if (positions.length === 0) {
    return {
      eyebrow: "First contract",
      title: "Scout an E-rank gate",
      copy: "It costs only ¤0.10. If discovery succeeds, you receive a finder stake and create a new asset for the market.",
      action: "Launch first expedition",
      to: "/discover",
      tone: "gold",
    };
  }
  return {
    eyebrow: "Portfolio online",
    title: "Turn ownership into cycle income",
    copy: "Inspect your gates, compare stability against yield, and expand only when the risk is worth the reward.",
    action: "Review your holdings",
    to: "/profile",
    tone: "violet",
  };
}

function plainRisk(risk: string): string {
  const labels: Record<string, string> = { STABLE: "Safe", WATCH: "Watch", CRITICAL: "Danger", OFFERING: "Not active", COLLAPSED: "Lost" };
  return labels[risk] ?? risk.replace(/_/g, " ").toLowerCase();
}

function plainCategory(category: string): string {
  const labels: Record<string, string> = { EVENT: "World omen", GATE: "Gate report", MARKET: "Market move", GUILD: "Guild report", LEADERBOARD: "Season report", WORLD: "World dispatch" };
  return labels[category] ?? category.replace(/_/g, " ").toLowerCase();
}
