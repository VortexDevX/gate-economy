import { useState } from "react";
import { useMyIntents, useMyOrders, useSubmitIntent } from "../../hooks/queries";
import { formatCurrency, shortId } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import { Badge } from "../../components/StatusBadge";

type Variant =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "orange"
  | "yellow";

const PAGE_SIZE = 20;

const orderStatusColors: Record<string, Variant> = {
  OPEN: "blue",
  PARTIAL: "amber",
  FILLED: "green",
  CANCELLED: "gray",
};

const sideColors: Record<string, Variant> = {
  BUY: "green",
  SELL: "red",
};

export default function OrdersPage() {
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const { data, isLoading, error, refetch } = useMyOrders({
    limit: PAGE_SIZE,
    offset,
  });
  const { data: intentsData } = useMyIntents({ limit: 10, offset: 0 });
  const cancelIntent = useSubmitIntent();
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleCancel = async (orderId: string) => {
    setCancellingId(orderId);
    try {
      await cancelIntent.mutateAsync({
        intent_type: "CANCEL_ORDER",
        payload: { order_id: orderId },
      });
      setTimeout(() => refetch(), 1000);
    } catch {
      // mutation handles the error state
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div>
        <h1 className="nm-page-title font-bold">Orders</h1>
        <p className="nm-page-subtitle mt-1">
          Intents are queued first, then executed during simulation ticks.
        </p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-2">
        <h2 className="nm-panel-title">Intent Timeline</h2>
        {!intentsData || intentsData.items.length === 0 ? (
          <div className="nm-soft-note">No recent intents submitted.</div>
        ) : (
          <ul className="space-y-2">
            {intentsData.items.slice(0, 8).map((intent) => (
              <li
                key={intent.id}
                className="text-xs border border-gray-800 rounded px-3 py-2 flex flex-col gap-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-gray-400">
                    {intent.intent_type} - {shortId(intent.id)}
                  </span>
                  <Badge
                    label={intent.status}
                    variant={
                      intent.status === "REJECTED"
                        ? "red"
                        : intent.status === "EXECUTED"
                          ? "green"
                          : "blue"
                    }
                  />
                </div>
                {intent.reject_reason && (
                  <div className="text-red-400">{intent.reject_reason}</div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorAlert message="Failed to load orders" />}
      {data && data.orders.length === 0 && (
        <EmptyState message="No orders yet. Open a gate and place your first order intent." />
      )}

      {data && data.orders.length > 0 && (
        <>
          <div className="nm-soft-note">{data.total} total orders</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="py-2 pr-3">Side</th>
                  <th className="py-2 pr-3">Asset</th>
                  <th className="py-2 pr-3">Price</th>
                  <th className="py-2 pr-3">Qty</th>
                  <th className="py-2 pr-3">Filled</th>
                  <th className="py-2 pr-3">Escrow</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Tick</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {data.orders.map((order) => {
                  const canCancel =
                    order.status === "OPEN" || order.status === "PARTIAL";
                  return (
                    <tr
                      key={order.id}
                      className="border-b border-gray-800/50 hover:bg-gray-900/50"
                    >
                      <td className="py-2 pr-3">
                        <Badge
                          label={order.side}
                          variant={sideColors[order.side] || "gray"}
                        />
                      </td>
                      <td className="py-2 pr-3">
                        <div className="text-xs">
                          <span className="text-gray-400">
                            {order.asset_type === "GATE_SHARE"
                              ? "Gate"
                              : "Guild"}
                          </span>{" "}
                          <span className="font-mono">
                            {shortId(order.asset_id)}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        ¤ {formatCurrency(order.price_limit_micro)}
                      </td>
                      <td className="py-2 pr-3">{order.quantity}</td>
                      <td className="py-2 pr-3">
                        <span
                          className={
                            order.filled_quantity > 0
                              ? "text-brand-400"
                              : "text-gray-500"
                          }
                        >
                          {order.filled_quantity}/{order.quantity}
                        </span>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs text-gray-400">
                        {order.escrow_micro > 0
                          ? `¤ ${formatCurrency(order.escrow_micro)}`
                          : "-"}
                      </td>
                      <td className="py-2 pr-3">
                        <Badge
                          label={order.status}
                          variant={orderStatusColors[order.status] || "gray"}
                        />
                      </td>
                      <td className="py-2 pr-3 text-gray-400 text-xs">
                        #{order.created_at_tick}
                      </td>
                      <td className="py-2 text-right">
                        {canCancel && (
                          <button
                            onClick={() => handleCancel(order.id)}
                            disabled={cancellingId === order.id}
                            className="text-xs text-red-400 hover:text-red-300
                                       disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {cancellingId === order.id
                              ? "Cancelling..."
                              : "Cancel"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {totalPages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
