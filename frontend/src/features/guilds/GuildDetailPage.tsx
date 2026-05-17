import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuthStore } from "../../stores/auth";
import { useGuild, useMarketPrice, useOrderBook, useTrades, useSubmitIntent } from "../../hooks/queries";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import { Badge } from "../../components/StatusBadge";
import { formatCurrency, formatPercent, shortId } from "../../utils/format";
import OrderBook from "../market/OrderBook";
import TradeHistory from "../market/TradeHistory";
import OrderForm from "../market/OrderForm";

const guildStatusColors: Record<string, "green" | "amber" | "red" | "gray"> = {
  ACTIVE: "green",
  INSOLVENT: "amber",
  DISSOLVED: "red",
};

export default function GuildDetailPage() {
  const { guildId } = useParams<{ guildId: string }>();
  const player = useAuthStore((s) => s.player);
  const submitIntent = useSubmitIntent();

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
  if (error || !guild) return <ErrorAlert message="Guild not found or failed to load" />;

  const visibleAskQty =
    orderBook?.asks.reduce((sum, level) => sum + level.total_quantity, 0) ?? 0;

  const isLeader =
    !!player &&
    guild.members.some((m) => m.player_id === player.id && m.role === "LEADER");
  const canManage = isLeader && guild.status === "ACTIVE";

  const onDividendSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setActionErr("");
    setActionMsg("");
    const amount = dividendAmount.trim();
    const payload: Record<string, unknown> = { guild_id: guild.id };
    if (amount) {
      const amountMicro = Math.round(Number(amount) * 1_000_000);
      if (!Number.isFinite(amountMicro) || amountMicro <= 0) {
        setActionErr("Dividend amount must be a positive number.");
        return;
      }
      payload.amount_micro = amountMicro;
    }
    try {
      await submitIntent.mutateAsync({
        intent_type: "GUILD_DIVIDEND",
        payload,
      });
      setActionMsg("Dividend intent queued.");
      setDividendAmount("");
    } catch {
      setActionErr("Failed to submit dividend intent.");
    }
  };

  const onInvestSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setActionErr("");
    setActionMsg("");

    const quantity = parseInt(investQty, 10);
    const priceMicro = Math.round(Number(investPrice) * 1_000_000);
    if (!investGateId.trim()) {
      setActionErr("Gate ID is required.");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setActionErr("Quantity must be a positive integer.");
      return;
    }
    if (!Number.isFinite(priceMicro) || priceMicro <= 0) {
      setActionErr("Price must be greater than zero.");
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
      setActionMsg("Guild invest intent queued.");
      setInvestGateId("");
      setInvestQty("1");
      setInvestPrice("");
    } catch {
      setActionErr("Failed to submit guild invest intent.");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <Link to="/guilds" className="text-sm text-gray-400 hover:text-gray-200">
        Back to Guilds
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <div><h1 className="nm-page-title font-bold">{guild.name}</h1><p className="nm-page-subtitle mt-1">Manage guild strategy, share trading, and treasury actions.</p></div>
        <Badge
          label={guild.status}
          variant={guildStatusColors[guild.status] || "gray"}
        />
        <span className="text-xs font-mono text-gray-500">{shortId(guild.id)}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Treasury">{formatCurrency(guild.treasury_micro)}</Stat>
        <Stat label="Total Shares">{guild.total_shares}</Stat>
        <Stat label="Public Float">{formatPercent(guild.public_float_pct)}</Stat>
        <Stat label="Maintenance">{formatCurrency(guild.maintenance_cost_micro)}</Stat>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
          <h2 className="text-sm uppercase tracking-wider text-gray-400">Members</h2>
          {guild.members.length === 0 ? (
            <div className="text-sm text-gray-500">No members</div>
          ) : (
            <ul className="space-y-2">
              {guild.members.map((m) => (
                <li key={m.player_id} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-xs">{shortId(m.player_id)}</span>
                  <Badge label={m.role} variant={m.role === "LEADER" ? "blue" : "gray"} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
          <h2 className="text-sm uppercase tracking-wider text-gray-400">Gate Holdings</h2>
          {guild.gate_holdings.length === 0 ? (
            <div className="text-sm text-gray-500">No gate holdings</div>
          ) : (
            <ul className="space-y-2">
              {guild.gate_holdings.map((h) => (
                <li key={h.gate_id} className="flex items-center justify-between text-sm">
                  <Link to={`/gates/${h.gate_id}`} className="font-mono text-xs text-brand-400 hover:text-brand-300">
                    {shortId(h.gate_id)}
                  </Link>
                  <span>{h.quantity} shares</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Guild Share Order Book</h2>
          <OrderBook
            data={orderBook}
            isLoading={orderBookLoading}
            onPriceClick={(p) => setPrefilledPrice(p)}
          />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Trade Guild Shares</h2>
          <OrderForm
            assetType="GUILD_SHARE"
            assetId={guild.id}
            marketPrice={marketPrice}
            prefilledPrice={prefilledPrice}
            visibleAskQty={visibleAskQty}
          />
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Guild Share Trade History</h2>
        <TradeHistory data={trades} isLoading={tradesLoading} />
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-4">
        <h2 className="text-sm uppercase tracking-wider text-gray-400">Leader Actions</h2>
        {!canManage ? (
          <div className="text-sm text-gray-500">
            Only active guild leaders can submit dividend/invest intents.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <form onSubmit={onDividendSubmit} className="space-y-2 border border-gray-800 rounded p-3">
              <h3 className="text-sm font-medium">Issue Dividend</h3>
              <p className="text-xs text-gray-500">
                Leave amount empty to distribute full guild treasury.
              </p>
              <input
                type="number"
                step="0.000001"
                min="0"
                placeholder="Amount in currency (optional)"
                value={dividendAmount}
                onChange={(e) => setDividendAmount(e.target.value)}
                className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                           focus:outline-none focus:border-brand-500"
              />
              <button
                type="submit"
                className="w-full bg-blue-700 hover:bg-blue-600 text-white text-sm py-2 rounded"
              >
                Queue Dividend Intent
              </button>
            </form>

            <form onSubmit={onInvestSubmit} className="space-y-2 border border-gray-800 rounded p-3">
              <h3 className="text-sm font-medium">Guild Invest In Gate</h3>
              <input
                value={investGateId}
                onChange={(e) => setInvestGateId(e.target.value)}
                placeholder="Gate UUID"
                className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                           focus:outline-none focus:border-brand-500 font-mono"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  min="1"
                  value={investQty}
                  onChange={(e) => setInvestQty(e.target.value)}
                  placeholder="Quantity"
                  className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                             focus:outline-none focus:border-brand-500"
                />
                <input
                  type="number"
                  min="0.000001"
                  step="0.000001"
                  value={investPrice}
                  onChange={(e) => setInvestPrice(e.target.value)}
                  placeholder="Price"
                  className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                             focus:outline-none focus:border-brand-500"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-amber-700 hover:bg-amber-600 text-white text-sm py-2 rounded"
              >
                Queue Guild Invest Intent
              </button>
            </form>
          </div>
        )}

        {actionErr && (
          <div className="text-xs text-red-300 bg-red-900/30 border border-red-800 rounded px-3 py-2">
            {actionErr}
          </div>
        )}
        {actionMsg && (
          <div className="text-xs text-green-300 bg-green-900/30 border border-green-800 rounded px-3 py-2">
            {actionMsg}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm font-mono">{children}</div>
    </div>
  );
}

