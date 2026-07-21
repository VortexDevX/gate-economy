import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Coins,
  History,
  Info,
  Landmark,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import {
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  RankCrest,
  StabilityMeter,
  StatRune,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import {
  useGate,
  useGateRankProfiles,
  useMarketHistory,
  useMarketPrice,
  useMyPortfolio,
  useOrderBook,
  useTrades,
} from "../../hooks/queries";
import { formatCurrency, formatCurrencyCompact, shortId } from "../../utils/format";
import GatePulse from "../market/GatePulse";
import OrderBook from "../market/OrderBook";
import OrderForm from "../market/OrderForm";
import TradeHistory from "../market/TradeHistory";

export default function GateDetailPage() {
  const { gateId } = useParams<{ gateId: string }>();
  const assetId = gateId ?? "";
  const gateQuery = useGate(assetId);
  const { data: rankProfiles } = useGateRankProfiles();
  const bookQuery = useOrderBook("GATE_SHARE", assetId);
  const tradesQuery = useTrades("GATE_SHARE", assetId, { limit: 20 });
  const priceQuery = useMarketPrice("GATE_SHARE", assetId);
  const historyQuery = useMarketHistory("GATE_SHARE", assetId, 60);
  const portfolioQuery = useMyPortfolio();
  const [prefilledPrice, setPrefilledPrice] = useState<number | null>(null);

  const gate = gateQuery.data;
  const rankProfile = useMemo(
    () => rankProfiles?.find((profile) => profile.rank === gate?.rank),
    [gate?.rank, rankProfiles],
  );

  if (gateQuery.isLoading) return <LoadingSpinner className="py-24" />;
  if (gateQuery.error || !gate) return <ErrorAlert message="This gate could not be found in the atlas." />;

  const position = portfolioQuery.data?.gate_positions.find((candidate) => candidate.gate_id === gate.id);
  const collapseThreshold = position?.collapse_threshold ?? rankProfile?.collapse_threshold ?? 30;
  const riskBand = position?.risk_band ?? inferRisk(gate.status, gate.stability, collapseThreshold);
  const marketPrice = priceQuery.data;
  const markPrice = position?.mark_price_micro ?? marketPrice?.last_price_micro ?? marketPrice?.best_ask_micro ?? marketPrice?.best_bid_micro ?? 0;
  const visibleAskQty = bookQuery.data?.asks.reduce((sum, level) => sum + level.total_quantity, 0) ?? 0;
  const yieldRate = markPrice > 0 ? (gate.yield_per_share_micro / markPrice) * 100 : null;
  const isCollapsed = gate.status === "COLLAPSED";
  const isEarning = gate.status === "ACTIVE";

  return (
    <div className="game-page gate-chamber-page">
      <Link to="/gates" className="game-back-link"><ArrowLeft size={16} aria-hidden="true" /> Back to Gate Atlas</Link>

      <section className={`gate-hero gate-hero-${gate.status.toLowerCase()}`}>
        <div className="gate-hero-portal" aria-hidden="true">
          <span className="gate-hero-ring gate-hero-ring-one" />
          <span className="gate-hero-ring gate-hero-ring-two" />
          <span className="gate-hero-core"><RankCrest rank={gate.rank} size="lg" /></span>
        </div>
        <div className="gate-hero-copy">
          <div className="gate-hero-badges">
            <span className="gate-ticker">{gate.ticker}</span>
            <span className={`gate-state gate-state-${gate.status.toLowerCase()}`}>{plainStatus(gate.status)}</span>
            <span className={`risk-word risk-${riskBand.toLowerCase()}`}>{plainRisk(riskBand)}</span>
          </div>
          <h1>{gate.display_name}</h1>
          <p>{gateStatusExplanation(gate.status)}</p>
          <StabilityMeter value={gate.stability} threshold={collapseThreshold} />
        </div>
        <div className="gate-hero-mark">
          <span>One share</span>
          <strong>{markPrice ? `¤ ${formatCurrency(markPrice)}` : "No price yet"}</strong>
          <small>{isEarning ? `+¤ ${formatCurrency(gate.yield_per_share_micro)} income each cycle` : gate.status === "OFFERING" ? "Income begins after activation" : "This gate is not producing income"}</small>
        </div>
      </section>

      {(priceQuery.error || portfolioQuery.error) && (
        <ErrorAlert message="Some live market or position data is unavailable. Gate lifecycle data remains visible." />
      )}

      <section className="gate-chamber-grid">
        <div className="gate-chamber-main">
          <div className="gate-stat-grid">
            <StatRune label="Income / share" value={isEarning ? `+¤ ${formatCurrency(gate.yield_per_share_micro)}` : "¤ 0.00"} note={isEarning ? `${yieldRate?.toFixed(2) ?? "—"}% of current price per cycle` : "Only Active gates produce income"} tone={isEarning ? "good" : "muted"} icon={<Coins size={18} />} />
            <StatRune label="Safety buffer" value={`${Math.max(0, gate.stability - collapseThreshold).toFixed(1)} pts`} note={`Collapse line for rank ${gate.rank === "S_PLUS" ? "S+" : gate.rank}: ${collapseThreshold}%`} tone={gate.stability - collapseThreshold <= 10 ? "danger" : "aether"} icon={<ShieldCheck size={18} />} />
            <StatRune label="Market activity" value={`¤ ${formatCurrencyCompact(marketPrice?.volume_24h_micro ?? 0)}`} note="Recent matched trade value" tone="violet" icon={<History size={18} />} />
            <StatRune label="Shares issued" value={String(gate.total_shares)} note={`${gate.shareholders.length} disclosed holder${gate.shareholders.length === 1 ? "" : "s"}`} tone="gold" icon={<Users size={18} />} />
          </div>

          <GamePanel className="gate-chart-panel" accent="aether">
            <PanelHeading title="Gate pulse" detail="Price movement and stability across recent world cycles." />
            <div className="gate-chart-scroll">
              <GatePulse
                points={historyQuery.data?.points}
                stability={gate.stability}
                status={gate.status}
                isLoading={historyQuery.isLoading}
                hasError={Boolean(historyQuery.error)}
              />
            </div>
          </GamePanel>

          <GamePanel className="position-panel" accent={position ? "gold" : "muted"}>
            <PanelHeading title="Your stake in this gate" detail="What you own, what it is worth, and what it may pay next cycle." />
            {portfolioQuery.isLoading && <LoadingSpinner />}
            {!portfolioQuery.isLoading && !position && (
              <GameEmpty title="You do not own this gate" message="Use the trade ticket to buy shares, or discover a new gate to earn a finder stake." />
            )}
            {position && (
              <div className="position-summary-grid">
                <div><span>Shares owned</span><strong>{position.quantity}</strong><small>{position.ownership_pct.toFixed(2)}% of the gate</small></div>
                <div><span>Current value</span><strong>¤ {formatCurrency(position.market_value_micro)}</strong><small>At the current mark price</small></div>
                <div><span>Next-cycle income</span><strong className="tone-good">+¤ {formatCurrency(position.projected_yield_micro)}</strong><small>{position.status === "ACTIVE" ? "If the gate remains active" : "Currently paused by gate state"}</small></div>
                <div><span>Best visible exit</span><strong>{position.best_bid_micro ? `¤ ${formatCurrency(position.best_bid_micro)}` : "No buyer"}</strong><small>Highest live bid per share</small></div>
              </div>
            )}
          </GamePanel>
        </div>

        <aside id="trade-ticket" className="gate-trade-column">
          <GamePanel className="gate-trade-panel" accent={isCollapsed ? "danger" : "gold"}>
            <div className="trade-panel-heading">
              <div><span className="game-eyebrow">Primary action</span><h2>{isCollapsed ? "Trading closed" : "Buy or sell shares"}</h2></div>
              {!isCollapsed && <Landmark size={24} aria-hidden="true" />}
            </div>
            <PlainTip>
              A buy reserves your coin; a sell reserves your shares. The order attempts to match on a world cycle.
            </PlainTip>
            {isCollapsed ? (
              <div className="collapsed-tombstone"><AlertTriangle size={28} /><strong>This gate collapsed at cycle {gate.collapsed_at_tick ?? "—"}</strong><span>Its shares are permanently worthless and no new trades can be placed.</span></div>
            ) : (
              <OrderForm
                assetType="GATE_SHARE"
                assetId={gate.id}
                marketPrice={marketPrice}
                prefilledPrice={prefilledPrice}
                visibleAskQty={visibleAskQty}
              />
            )}
          </GamePanel>

          <GamePanel className="gate-quick-read" accent="muted">
            <PanelHeading title="Read this gate" />
            <dl>
              <div><dt><ArrowUp size={14} /> Best buyer</dt><dd>{marketPrice?.best_bid_micro ? `¤ ${formatCurrency(marketPrice.best_bid_micro)}` : "None"}</dd></div>
              <div><dt><ArrowDown size={14} /> Cheapest seller</dt><dd>{marketPrice?.best_ask_micro ? `¤ ${formatCurrency(marketPrice.best_ask_micro)}` : "None"}</dd></div>
              <div><dt><Sparkles size={14} /> Discovery</dt><dd>{plainDiscovery(gate.discovery_type)} · cycle {gate.spawned_at_tick}</dd></div>
              <div><dt><Info size={14} /> Gate record</dt><dd>{shortId(gate.id)}</dd></div>
            </dl>
          </GamePanel>
        </aside>
      </section>

      <details className="advanced-market" open={false}>
        <summary><span><Landmark size={19} /> Advanced market data</span><small>Order book, executed trades, and ownership concentration</small></summary>
        <div className="advanced-market-grid">
          <GamePanel accent="aether">
            <PanelHeading title="Live order book" detail="Select a price to copy it into the trade ticket." />
            {bookQuery.error ? <ErrorAlert message="Order book unavailable." /> : <OrderBook data={bookQuery.data} isLoading={bookQuery.isLoading} onPriceClick={setPrefilledPrice} />}
          </GamePanel>
          <GamePanel accent="muted">
            <PanelHeading title="Recent matched trades" />
            {tradesQuery.error ? <ErrorAlert message="Trade history unavailable." /> : <TradeHistory data={tradesQuery.data} isLoading={tradesQuery.isLoading} />}
          </GamePanel>
          <GamePanel accent="violet" className="advanced-holders">
            <PanelHeading title="Who owns the gate" detail={`${gate.shareholders.length} disclosed holders`} />
            {!gate.shareholders.length ? (
              <GameEmpty title="No player ownership yet" message="Finder stakes and completed trades will appear here." />
            ) : (
              <div className="holder-list">
                {gate.shareholders.map((holder) => (
                  <div key={holder.player_id}><span>{shortId(holder.player_id)}</span><strong>{holder.quantity} shares</strong><small>{holder.percentage.toFixed(1)}%</small></div>
                ))}
              </div>
            )}
          </GamePanel>
        </div>
      </details>

      {!isCollapsed && <a href="#trade-ticket" className="mobile-trade-jump">Trade this gate</a>}
    </div>
  );
}

function inferRisk(status: string, stability: number, threshold: number): string {
  if (status === "COLLAPSED") return "COLLAPSED";
  if (status === "OFFERING") return "OFFERING";
  const buffer = stability - threshold;
  if (buffer <= 10) return "CRITICAL";
  if (buffer <= 30) return "WATCH";
  return "STABLE";
}

function plainStatus(status: string) {
  return ({ OFFERING: "Preparing", ACTIVE: "Earning", UNSTABLE: "In danger", COLLAPSED: "Collapsed" } as Record<string, string>)[status] ?? status;
}
function plainRisk(risk: string) {
  return ({ STABLE: "Safe", WATCH: "Watch closely", CRITICAL: "Collapse danger", OFFERING: "Not active", COLLAPSED: "Lost" } as Record<string, string>)[risk] ?? risk;
}
function plainDiscovery(type: string) {
  return ({ PLAYER: "Player expedition", SYSTEM: "World event" } as Record<string, string>)[type] ?? type.replace(/_/g, " ").toLowerCase();
}
function gateStatusExplanation(status: string) {
  const copy: Record<string, string> = {
    OFFERING: "This gate is newly discovered. Shares may trade now, but it will not produce income until it activates.",
    ACTIVE: "This gate is producing income every completed world cycle. The opportunity lasts only while stability holds.",
    UNSTABLE: "Income has stopped. The gate is inside its collapse corridor, so remaining share value is in serious danger.",
    COLLAPSED: "The gate is gone. Trading is closed and all remaining shares have lost their value.",
  };
  return copy[status] ?? "A volatile gate-share instrument in the Obsidian Exchange.";
}
