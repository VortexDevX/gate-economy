import { useId, useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock3,
  Coins,
  Crown,
  LineChart,
  Scale,
  Shield,
  ShieldAlert,
  TrendingUp,
  UsersRound,
  Vault,
} from "lucide-react";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import { Badge } from "../../components/StatusBadge";
import {
  GameButton,
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
import {
  useGuild,
  useMarketPrice,
  useOrderBook,
  useSubmitIntent,
  useTrades,
} from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency, formatPercent, shortId } from "../../utils/format";
import OrderForm from "../market/OrderForm";
import OrderBook from "../market/OrderBook";
import TradeHistory from "../market/TradeHistory";

const guildStatusColors: Record<string, "green" | "amber" | "red" | "gray"> = {
  ACTIVE: "green",
  INSOLVENT: "amber",
  DISSOLVED: "red",
};

export default function GuildDetailPage() {
  const { guildId } = useParams<{ guildId: string }>();
  const player = useAuthStore((state) => state.player);
  const submitIntent = useSubmitIntent();
  const dividendId = useId();
  const gateId = useId();
  const quantityId = useId();
  const priceId = useId();

  const { data: guild, isLoading, error } = useGuild(guildId || "");
  const { data: marketPrice } = useMarketPrice("GUILD_SHARE", guildId || "");
  const { data: orderBook, isLoading: orderBookLoading } = useOrderBook(
    "GUILD_SHARE",
    guildId || "",
  );
  const { data: trades, isLoading: tradesLoading } = useTrades(
    "GUILD_SHARE",
    guildId || "",
    { limit: 20 },
  );

  const [dividendAmount, setDividendAmount] = useState("");
  const [investGateId, setInvestGateId] = useState("");
  const [investQty, setInvestQty] = useState("1");
  const [investPrice, setInvestPrice] = useState("");
  const [actionMsg, setActionMsg] = useState("");
  const [actionErr, setActionErr] = useState("");
  const [prefilledPrice, setPrefilledPrice] = useState<number | null>(null);

  if (isLoading) return <LoadingSpinner />;
  if (error || !guild) {
    return <ErrorAlert message="This guild hall could not be opened. No treasury, shares, or membership changed." />;
  }

  const visibleAskQty =
    orderBook?.asks.reduce((sum, level) => sum + level.total_quantity, 0) ?? 0;
  const isLeader =
    !!player && guild.members.some((member) => member.player_id === player.id && member.role === "LEADER");
  const canManage = isLeader && guild.status === "ACTIVE";
  const treasuryCycles = guild.maintenance_cost_micro > 0
    ? guild.treasury_micro / guild.maintenance_cost_micro
    : null;

  const onDividendSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setActionErr("");
    setActionMsg("");
    const amount = dividendAmount.trim();
    const payload: Record<string, unknown> = { guild_id: guild.id };
    if (amount) {
      const amountMicro = Math.round(Number(amount) * 1_000_000);
      if (!Number.isFinite(amountMicro) || amountMicro <= 0) {
        setActionErr("Enter a positive dividend amount, or leave it empty to distribute the full treasury.");
        return;
      }
      payload.amount_micro = amountMicro;
    }
    try {
      await submitIntent.mutateAsync({
        intent_type: "GUILD_DIVIDEND",
        payload,
      });
      setActionMsg(
        "Dividend command queued. No coin has moved yet; the next cycle will validate the treasury and pay guild shareholders.",
      );
      setDividendAmount("");
    } catch {
      setActionErr("The dividend command could not be queued. The guild treasury was not changed.");
    }
  };

  const onInvestSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setActionErr("");
    setActionMsg("");

    const quantity = parseInt(investQty, 10);
    const priceMicro = Math.round(Number(investPrice) * 1_000_000);
    if (!investGateId.trim()) {
      setActionErr("Copy a gate ID from the Gate Atlas before investing guild coin.");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setActionErr("Share quantity must be a positive whole number.");
      return;
    }
    if (!Number.isFinite(priceMicro) || priceMicro <= 0) {
      setActionErr("Maximum price per share must be greater than zero.");
      return;
    }

    try {
      await submitIntent.mutateAsync({
        intent_type: "GUILD_INVEST",
        payload: {
          guild_id: guild.id,
          gate_id: investGateId.trim(),
          quantity,
          price_limit_micro: priceMicro,
        },
      });
      setActionMsg(
        "Guild investment queued. The next cycle will validate the gate, price limit, and available treasury before creating the order.",
      );
      setInvestGateId("");
      setInvestQty("1");
      setInvestPrice("");
    } catch {
      setActionErr("The investment command could not be queued. No guild coin was committed.");
    }
  };

  return (
    <div className="game-page guild-command-page grid gap-[18px]">
      <ScreenHeader
        eyebrow={`Guild command · Founded cycle ${guild.created_at_tick}`}
        title={guild.name}
        description="Inspect the treasury runway, members, gate holdings, and guild-share market before trading. Leaders can issue treasury commands from the war room below."
        action={(
          <Link to="/guilds" className="game-action game-action-ghost guild-command-back">
            <ArrowLeft size={17} aria-hidden="true" />
            <span>Return to Guild Hall</span>
          </Link>
        )}
      />

      <div className="guild-command-identity flex flex-wrap items-center gap-2 border border-[var(--line)] bg-black/10 px-3 py-2">
        <Shield size={18} className="tone-violet" aria-hidden="true" />
        <Badge label={plainGuildStatus(guild.status)} variant={guildStatusColors[guild.status] || "gray"} />
        <span className="text-xs text-[var(--muted)]">Guild record {shortId(guild.id)}</span>
        {isLeader && (
          <span className="ml-auto flex items-center gap-1 text-xs font-bold uppercase tracking-wide tone-gold">
            <Crown size={15} aria-hidden="true" /> You lead this guild
          </span>
        )}
      </div>

      <section className="guild-command-stats grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4" aria-label="Guild economy summary">
        <StatRune
          label="Treasury"
          value={`¤ ${formatCurrency(guild.treasury_micro)}`}
          note={treasuryCycles == null ? "No recurring upkeep recorded" : `${treasuryCycles.toFixed(1)} cycles of current upkeep held`}
          tone={treasuryCycles != null && treasuryCycles < 3 ? "danger" : "gold"}
          icon={<Vault size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Guild shares"
          value={String(guild.total_shares)}
          note={`${formatPercent(guild.public_float_pct)} may trade publicly`}
          tone="violet"
          icon={<Scale size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Upkeep each cycle"
          value={`¤ ${formatCurrency(guild.maintenance_cost_micro)}`}
          note="Paid from the treasury while the guild operates"
          tone="warn"
          icon={<Clock3 size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Guild shareholders"
          value={String(guild.shareholder_count)}
          note={plainDividendPolicy(guild.dividend_policy, guild.auto_dividend_pct)}
          tone="aether"
          icon={<UsersRound size={18} aria-hidden="true" />}
        />
      </section>

      {guild.status === "INSOLVENT" && (
        <div className="guild-command-danger flex items-start gap-2 border border-amber-800 bg-amber-900/15 px-3 py-3 text-sm text-amber-200" role="status">
          <ShieldAlert size={19} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>This treasury cannot safely meet its obligations. Inspect the runway before buying guild shares.</span>
        </div>
      )}

      <div className="guild-command-roster grid grid-cols-1 gap-4 lg:grid-cols-2">
        <GamePanel className="guild-command-members p-5" accent="violet">
          <PanelHeading
            title="Banner roster"
            detail="Members may participate in the guild; only the leader can command its treasury."
            action={<span className="game-badge game-badge-purple">{guild.members.length} members</span>}
          />
          {guild.members.length === 0 ? (
            <GameEmpty title="No names on this banner" message="This guild currently has no recorded members." />
          ) : (
            <ul className="grid gap-2" aria-label="Guild members">
              {guild.members.map((member) => (
                <li key={member.player_id} className="guild-command-member flex items-center gap-3 border border-[var(--line)] bg-black/10 p-3">
                  <span className="grid size-9 shrink-0 place-items-center border border-[var(--line-bright)] tone-violet">
                    {member.role === "LEADER" ? <Crown size={17} aria-hidden="true" /> : <Shield size={17} aria-hidden="true" />}
                  </span>
                  <div className="min-w-0">
                    <strong className="block truncate font-mono text-xs">Hunter {shortId(member.player_id)}</strong>
                    <small className="block text-[10px] text-[var(--muted)]">Joined in cycle {member.joined_at_tick}</small>
                  </div>
                  <Badge label={member.role === "LEADER" ? "Guild leader" : "Member"} variant={member.role === "LEADER" ? "blue" : "gray"} />
                </li>
              ))}
            </ul>
          )}
        </GamePanel>

        <GamePanel className="guild-command-holdings p-5" accent="aether">
          <PanelHeading
            title="Gate holdings"
            detail="Gate shares owned by the shared treasury, exposed to each gate's yield and collapse risk."
            action={<span className="game-badge game-badge-blue">{guild.gate_holdings.length} gates</span>}
          />
          {guild.gate_holdings.length === 0 ? (
            <GameEmpty
              title="Treasury owns no gates"
              message="A leader can queue a gate investment from the war room after checking the Gate Atlas."
              action={{ to: "/gates", label: "Inspect the Gate Atlas" }}
            />
          ) : (
            <ul className="grid gap-2" aria-label="Guild gate holdings">
              {guild.gate_holdings.map((holding) => (
                <li key={holding.gate_id} className="guild-command-holding flex items-center gap-3 border border-[var(--line)] bg-black/10 p-3">
                  <span className="grid size-9 shrink-0 place-items-center border border-[var(--line-bright)] tone-aether">
                    <TrendingUp size={17} aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <Link to={`/gates/${holding.gate_id}`} className="block truncate font-mono text-xs tone-aether">
                      Gate {shortId(holding.gate_id)}
                    </Link>
                    <small className="text-[10px] text-[var(--muted)]">Shared treasury position</small>
                  </div>
                  <strong className="font-mono text-sm">{holding.quantity} shares</strong>
                </li>
              ))}
            </ul>
          )}
        </GamePanel>
      </div>

      <PlainTip>
        Guild shares represent the guild itself, not one gate. Their value depends on the treasury, policies, and every gate position the guild owns.
      </PlainTip>

      <section className="guild-command-market grid grid-cols-1 gap-4 xl:grid-cols-2" aria-label="Guild share exchange">
        <GamePanel className="guild-command-book p-5" accent="aether">
          <PanelHeading
            title="Guild share order book"
            detail="Click a price level to copy it into your trade ticket."
            action={<BarChart3 size={19} className="tone-aether" aria-hidden="true" />}
          />
          <OrderBook
            data={orderBook}
            isLoading={orderBookLoading}
            onPriceClick={(price) => setPrefilledPrice(price)}
          />
        </GamePanel>
        <GamePanel className="guild-command-trade gate-trade-panel p-5" accent="gold">
          <PanelHeading
            title="Trade guild shares"
            detail="Set a maximum buy price or minimum sell price. Orders resolve on world cycles and may remain unmatched."
            action={<Scale size={19} className="tone-gold" aria-hidden="true" />}
          />
          <OrderForm
            assetType="GUILD_SHARE"
            assetId={guild.id}
            marketPrice={marketPrice}
            prefilledPrice={prefilledPrice}
            visibleAskQty={visibleAskQty}
          />
        </GamePanel>
      </section>

      <GamePanel className="guild-command-history p-5" accent="muted">
        <PanelHeading
          title="Completed guild-share trades"
          detail="Only matched trades appear here; open orders remain in Orders & Results."
          action={<LineChart size={19} className="text-[var(--muted)]" aria-hidden="true" />}
        />
        <TradeHistory data={trades} isLoading={tradesLoading} />
      </GamePanel>

      <GamePanel className="guild-command-war-room p-5 sm:p-6" accent={canManage ? "violet" : "muted"}>
        <PanelHeading
          title="Leader war room"
          detail="Treasury commands are powerful, cycle-based, and visible to guild shareholders."
          action={<Crown size={20} className={canManage ? "tone-violet" : "text-[var(--muted)]"} aria-hidden="true" />}
        />
        {!canManage ? (
          <div className="guild-command-locked flex items-start gap-3 border border-[var(--line)] bg-black/10 p-4 text-sm text-[var(--muted)]">
            <Shield size={20} className="shrink-0" aria-hidden="true" />
            <span>{isLeader
              ? "Treasury commands are locked because this guild is not operating."
              : "Only the leader of an operating guild can issue dividends or invest treasury coin."}</span>
          </div>
        ) : (
          <div className="guild-command-actions grid grid-cols-1 gap-4 xl:grid-cols-2">
            <form onSubmit={onDividendSubmit} className="guild-command-action grid content-start gap-3 border border-[var(--line)] bg-black/10 p-4">
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center border border-[var(--line-bright)] tone-gold">
                  <Coins size={19} aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-sm uppercase">Reward guild shareholders</h3>
                  <p className="mt-1 text-xs text-[var(--muted)]">Pays coin from the treasury to every guild-share owner. Leaving the amount empty attempts to distribute the full treasury.</p>
                </div>
              </div>
              <CommandField label="Dividend amount in coin (optional)" htmlFor={dividendId}>
                <input
                  id={dividendId}
                  type="number"
                  step="0.000001"
                  min="0"
                  placeholder="Leave empty for the full treasury"
                  value={dividendAmount}
                  onChange={(e) => setDividendAmount(e.target.value)}
                  className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                  inputMode="decimal"
                />
              </CommandField>
              <GameButton type="submit" disabled={submitIntent.isPending} className="w-full">
                {submitIntent.isPending ? "Queueing command…" : "Queue dividend"}
              </GameButton>
            </form>

            <form onSubmit={onInvestSubmit} className="guild-command-action grid content-start gap-3 border border-[var(--line)] bg-black/10 p-4">
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center border border-[var(--line-bright)] tone-aether">
                  <TrendingUp size={19} aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-sm uppercase">Invest treasury in a gate</h3>
                  <p className="mt-1 text-xs text-[var(--muted)]">Creates a limit buy from guild coin. It may wait on the market if no seller accepts your price.</p>
                </div>
              </div>
              <CommandField label="Gate ID" htmlFor={gateId}>
                <input
                  id={gateId}
                  value={investGateId}
                  onChange={(e) => setInvestGateId(e.target.value)}
                  placeholder="Copy a UUID from the Gate Atlas"
                  className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                  autoComplete="off"
                />
              </CommandField>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <CommandField label="Share quantity" htmlFor={quantityId}>
                  <input
                    id={quantityId}
                    type="number"
                    min="1"
                    value={investQty}
                    onChange={(e) => setInvestQty(e.target.value)}
                    className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                    inputMode="numeric"
                  />
                </CommandField>
                <CommandField label="Maximum price per share" htmlFor={priceId}>
                  <input
                    id={priceId}
                    type="number"
                    min="0.000001"
                    step="0.000001"
                    value={investPrice}
                    onChange={(e) => setInvestPrice(e.target.value)}
                    placeholder="0.000000"
                    className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                    inputMode="decimal"
                  />
                </CommandField>
              </div>
              <GameButton type="submit" tone="secondary" disabled={submitIntent.isPending} className="w-full">
                {submitIntent.isPending ? "Queueing command…" : "Queue guild investment"}
              </GameButton>
            </form>
          </div>
        )}

        {actionErr && (
          <div className="guild-command-receipt mt-4 flex items-start gap-2 border border-red-800 bg-red-900/20 px-3 py-2 text-sm text-red-300" role="alert">
            <AlertTriangle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>{actionErr}</span>
          </div>
        )}
        {actionMsg && (
          <div className="guild-command-receipt mt-4 flex items-start gap-2 border border-green-800 bg-green-900/20 px-3 py-2 text-sm text-green-300" role="status">
            <CheckCircle2 size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>{actionMsg}</span>
          </div>
        )}
      </GamePanel>
    </div>
  );
}

function CommandField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div className="guild-command-field grid gap-1.5">
      <label htmlFor={htmlFor} className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
        {label}
      </label>
      {children}
    </div>
  );
}

function plainGuildStatus(status: string): string {
  const labels: Record<string, string> = {
    ACTIVE: "Operating",
    INSOLVENT: "Treasury in danger",
    DISSOLVED: "Closed",
  };
  return labels[status] ?? sentenceCase(status);
}

function plainDividendPolicy(policy: string, amount: number | null): string {
  if (policy === "AUTO_FIXED_PCT" || policy === "AUTO") {
    return amount == null ? "Automatic dividend policy" : `Automatically pays ${formatPercent(amount)}`;
  }
  if (policy === "MANUAL") return "Leader chooses each dividend";
  return sentenceCase(policy);
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
