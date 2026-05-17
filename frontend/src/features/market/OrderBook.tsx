import type { OrderBookResponse } from "../../api/types";
import { formatCurrency } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";

interface Props {
  data: OrderBookResponse | undefined;
  isLoading: boolean;
  onPriceClick?: (priceMicro: number) => void;
}

export default function OrderBook({ data, isLoading, onPriceClick }: Props) {
  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const maxBidQty = data.bids.reduce(
    (m, b) => Math.max(m, b.total_quantity),
    0,
  );
  const maxAskQty = data.asks.reduce(
    (m, a) => Math.max(m, a.total_quantity),
    0,
  );
  const maxQty = Math.max(maxBidQty, maxAskQty, 1);

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="grid grid-cols-3 text-xs text-gray-500 px-2 pb-1 border-b border-gray-800">
        <span>Price</span>
        <span className="text-right">Qty</span>
        <span className="text-right">Orders</span>
      </div>

      {/* Asks — show reversed so lowest ask is at bottom near spread */}
      <div className="max-h-40 overflow-y-auto flex flex-col-reverse">
        {data.asks.length === 0 ? (
          <div className="text-xs text-gray-600 text-center py-2">No asks</div>
        ) : (
          data.asks.map((entry) => (
            <div
              key={entry.price_micro}
              className="relative grid grid-cols-3 text-xs px-2 py-1 cursor-pointer rounded-md hover:bg-gray-800/50"
              onClick={() => onPriceClick?.(entry.price_micro)}
            >
              <div
                className="absolute inset-0 rounded-md"
                style={{
                  width: `${(entry.total_quantity / maxQty) * 100}%`,
                  right: 0,
                  left: "auto",
                  background: "rgba(205, 62, 62, 0.12)",
                }}
              />
              <span className="relative font-mono" style={{ color: "#b53b3b" }}>
                ¤ {formatCurrency(entry.price_micro)}
              </span>
              <span className="relative text-right font-mono">
                {entry.total_quantity}
              </span>
              <span className="relative text-right text-gray-500">
                {entry.order_count}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Spread indicator */}
      {data.bids.length > 0 && data.asks.length > 0 && (
        <div className="text-center text-xs text-gray-500 py-1 border-y border-gray-800">
          Spread: ¤{" "}
          {formatCurrency(data.asks[0].price_micro - data.bids[0].price_micro)}
        </div>
      )}

      {/* Bids */}
      <div className="max-h-40 overflow-y-auto">
        {data.bids.length === 0 ? (
          <div className="text-xs text-gray-600 text-center py-2">No bids</div>
        ) : (
          data.bids.map((entry) => (
            <div
              key={entry.price_micro}
              className="relative grid grid-cols-3 text-xs px-2 py-1 cursor-pointer rounded-md hover:bg-gray-800/50"
              onClick={() => onPriceClick?.(entry.price_micro)}
            >
              <div
                className="absolute inset-0 rounded-md"
                style={{
                  width: `${(entry.total_quantity / maxQty) * 100}%`,
                  right: 0,
                  left: "auto",
                  background: "rgba(39, 153, 95, 0.12)",
                }}
              />
              <span className="relative font-mono" style={{ color: "#1f7f51" }}>
                ¤ {formatCurrency(entry.price_micro)}
              </span>
              <span className="relative text-right font-mono">
                {entry.total_quantity}
              </span>
              <span className="relative text-right text-gray-500">
                {entry.order_count}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
