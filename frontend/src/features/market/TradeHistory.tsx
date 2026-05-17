import type { TradeListResponse } from "../../api/types";
import { formatCurrency, shortId } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import EmptyState from "../../components/EmptyState";

interface Props {
  data: TradeListResponse | undefined;
  isLoading: boolean;
}

export default function TradeHistory({ data, isLoading }: Props) {
  if (isLoading) return <LoadingSpinner />;
  if (!data || data.trades.length === 0)
    return <EmptyState message="No trades yet" />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800">
            <th className="py-1.5 pr-3">Tick</th>
            <th className="py-1.5 pr-3">Price</th>
            <th className="py-1.5 pr-3">Qty</th>
            <th className="py-1.5 pr-3">Value</th>
            <th className="py-1.5 pr-3">Buyer Fee</th>
            <th className="py-1.5">Seller Fee</th>
          </tr>
        </thead>
        <tbody>
          {data.trades.map((trade) => (
            <tr
              key={trade.id}
              className="border-b border-gray-800/50"
            >
              <td className="py-1.5 pr-3 text-gray-400">#{trade.tick_id}</td>
              <td className="py-1.5 pr-3 font-mono">
                ¤ {formatCurrency(trade.price_micro)}
              </td>
              <td className="py-1.5 pr-3">{trade.quantity}</td>
              <td className="py-1.5 pr-3 font-mono">
                ¤ {formatCurrency(trade.price_micro * trade.quantity)}
              </td>
              <td className="py-1.5 pr-3 font-mono text-gray-500">
                ¤ {formatCurrency(trade.buyer_fee_micro)}
              </td>
              <td className="py-1.5 font-mono text-gray-500">
                ¤ {formatCurrency(trade.seller_fee_micro)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
