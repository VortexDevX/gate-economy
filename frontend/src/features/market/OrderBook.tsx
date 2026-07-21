import type { OrderBookEntry, OrderBookResponse } from "../../api/types";
import { formatCurrency } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";

interface Props {
  data: OrderBookResponse | undefined;
  isLoading: boolean;
  onPriceClick?: (priceMicro: number) => void;
}

export default function OrderBook({ data, isLoading, onPriceClick }: Props) {
  if (isLoading) return <LoadingSpinner />;
  if (!data) {
    return (
      <div
        role="status"
        className="nm-soft-note text-center border border-gray-800 rounded px-3 py-6"
      >
        Order book unavailable. Live market feed will retry automatically.
      </div>
    );
  }

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
    <div className="space-y-1" aria-label="Market order book">
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
            <BookRow
              key={entry.price_micro}
              entry={entry}
              side="ask"
              maxQty={maxQty}
              onPriceClick={onPriceClick}
            />
          ))
        )}
      </div>

      {/* Spread indicator */}
      {data.bids.length > 0 && data.asks.length > 0 && (
        <div
          className="text-center text-xs text-gray-500 py-1 border-y border-gray-800"
          aria-live="polite"
        >
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
            <BookRow
              key={entry.price_micro}
              entry={entry}
              side="bid"
              maxQty={maxQty}
              onPriceClick={onPriceClick}
            />
          ))
        )}
      </div>
    </div>
  );
}

function BookRow({
  entry,
  side,
  maxQty,
  onPriceClick,
}: {
  entry: OrderBookEntry;
  side: "ask" | "bid";
  maxQty: number;
  onPriceClick?: (priceMicro: number) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onPriceClick?.(entry.price_micro)}
      disabled={!onPriceClick}
      className={`dge-book-row dge-book-row-${side} relative grid w-full grid-cols-3 px-2 py-1 text-xs text-left rounded-md`}
      aria-label={`Use ${side} price ${formatCurrency(entry.price_micro)} for ${entry.total_quantity} shares across ${entry.order_count} orders`}
    >
      <span
        className="dge-book-depth absolute inset-y-0 right-0 rounded-md"
        style={{ width: `${(entry.total_quantity / maxQty) * 100}%` }}
        aria-hidden="true"
      />
      <span className="dge-book-price relative font-mono">
        ¤ {formatCurrency(entry.price_micro)}
      </span>
      <span className="relative text-right font-mono">{entry.total_quantity}</span>
      <span className="relative text-right text-gray-500">{entry.order_count}</span>
    </button>
  );
}
