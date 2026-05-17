import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useGate,
  useOrderBook,
  useTrades,
  useMarketPrice,
} from "../../hooks/queries";
import { formatCurrency, formatStability, shortId } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import { GateRankBadge, GateStatusBadge } from "../../components/StatusBadge";
import OrderBook from "../market/OrderBook";
import TradeHistory from "../market/TradeHistory";
import OrderForm from "../market/OrderForm";

export default function GateDetailPage() {
  const { gateId } = useParams<{ gateId: string }>();
  const { data: gate, isLoading, error } = useGate(gateId || "");
  const { data: book, isLoading: bookLoading } = useOrderBook(
    "GATE_SHARE",
    gateId || "",
  );
  const { data: trades, isLoading: tradesLoading } = useTrades(
    "GATE_SHARE",
    gateId || "",
    { limit: 20 },
  );
  const { data: marketPrice } = useMarketPrice("GATE_SHARE", gateId || "");

  const [prefilledPrice, setPrefilledPrice] = useState<number | null>(null);

  if (isLoading) return <LoadingSpinner />;
  if (error || !gate)
    return <ErrorAlert message="Gate not found or failed to load" />;

  const stabClamped = Math.max(0, Math.min(100, gate.stability));
  const stabColor =
    stabClamped > 60
      ? "bg-green-500"
      : stabClamped > 30
        ? "bg-amber-500"
        : "bg-red-500";

  const isCollapsed = gate.status === "COLLAPSED";
  const visibleAskQty =
    book?.asks.reduce((sum, level) => sum + level.total_quantity, 0) ?? 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <Link to="/gates" className="text-sm text-gray-400 hover:text-gray-200">
          ← All Gates
        </Link>
        <h1 className="nm-page-title font-bold mt-2">Gate Market Detail</h1>
        <p className="nm-page-subtitle mt-1">
          Review liquidity, queue intents, and monitor holder concentration.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <GateRankBadge rank={gate.rank} />
        <GateStatusBadge status={gate.status} />
        <span className="text-gray-500 text-sm font-mono">{shortId(gate.id)}</span>
        {marketPrice?.last_price_micro && (
          <span className="ml-auto text-sm font-mono text-brand-300">
            Last: ¤ {formatCurrency(marketPrice.last_price_micro)}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <DetailStat label="Stability">
          <div className="flex items-center gap-2">
            <div className="w-16 h-2.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${stabColor}`}
                style={{ width: `${stabClamped}%` }}
              />
            </div>
            <span className="font-mono text-xs">{formatStability(gate.stability)}</span>
          </div>
        </DetailStat>
        <DetailStat label="Volatility">
          <span className="font-mono text-xs">{(gate.volatility * 100).toFixed(1)}%</span>
        </DetailStat>
        <DetailStat label="Base Yield / tick">
          <span className="font-mono text-xs">¤ {formatCurrency(gate.base_yield_micro)}</span>
        </DetailStat>
        <DetailStat label="Total Shares">
          <span className="font-mono text-xs">{gate.total_shares}</span>
        </DetailStat>
      </div>

      {marketPrice && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <DetailStat label="Best Bid">
            <span className="font-mono text-xs text-green-500">
              {marketPrice.best_bid_micro
                ? `¤ ${formatCurrency(marketPrice.best_bid_micro)}`
                : "-"}
            </span>
          </DetailStat>
          <DetailStat label="Best Ask">
            <span className="font-mono text-xs text-red-500">
              {marketPrice.best_ask_micro
                ? `¤ ${formatCurrency(marketPrice.best_ask_micro)}`
                : "-"}
            </span>
          </DetailStat>
          <DetailStat label="Last Price">
            <span className="font-mono text-xs">
              {marketPrice.last_price_micro
                ? `¤ ${formatCurrency(marketPrice.last_price_micro)}`
                : "-"}
            </span>
          </DetailStat>
          <DetailStat label="Volume (24h)">
            <span className="font-mono text-xs">
              ¤ {formatCurrency(marketPrice.volume_24h_micro)}
            </span>
          </DetailStat>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="nm-panel-title mb-3">Order Book</h2>
          <OrderBook
            data={book}
            isLoading={bookLoading}
            onPriceClick={(p) => setPrefilledPrice(p)}
          />
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="nm-panel-title mb-3">Queue Order Intent</h2>
          {isCollapsed ? (
            <div className="nm-soft-note text-center py-8">
              This gate has collapsed. Trading is permanently closed for this asset.
            </div>
          ) : (
            <OrderForm
              assetType="GATE_SHARE"
              assetId={gate.id}
              marketPrice={marketPrice}
              prefilledPrice={prefilledPrice}
              visibleAskQty={visibleAskQty}
            />
          )}
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="nm-panel-title mb-3">Recent Executed Trades</h2>
        <TradeHistory data={trades} isLoading={tradesLoading} />
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="nm-panel-title mb-3">Shareholders</h2>
        {gate.shareholders.length === 0 ? (
          <div className="nm-soft-note text-center py-4">
            No shares distributed yet. First fills appear after successful buy intents.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800">
                <th className="py-2 pr-4">Holder</th>
                <th className="py-2 pr-4">Shares</th>
                <th className="py-2">Ownership</th>
              </tr>
            </thead>
            <tbody>
              {gate.shareholders.map((sh) => (
                <tr key={sh.player_id} className="border-b border-gray-800/50">
                  <td className="py-2 pr-4 font-mono text-xs">{shortId(sh.player_id)}</td>
                  <td className="py-2 pr-4">{sh.quantity}</td>
                  <td className="py-2">{sh.percentage.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <DetailStat label="Spawned At">
          <span className="text-xs">Tick #{gate.spawned_at_tick}</span>
        </DetailStat>
        <DetailStat label="Discovery">
          <span className="text-xs">{gate.discovery_type}</span>
        </DetailStat>
        {gate.collapsed_at_tick && (
          <DetailStat label="Collapsed At">
            <span className="text-xs text-red-500">Tick #{gate.collapsed_at_tick}</span>
          </DetailStat>
        )}
        {gate.discoverer_id && (
          <DetailStat label="Discoverer">
            <span className="font-mono text-xs">{shortId(gate.discoverer_id)}</span>
          </DetailStat>
        )}
      </div>
    </div>
  );
}

function DetailStat({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      <div className="nm-panel-title mb-1">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

