import { useState } from "react";
import { useAuthStore } from "../../stores/auth";
import { useMyLedger } from "../../hooks/queries";
import { formatCurrency, formatDate, shortId } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";

export default function ProfilePage() {
  const player = useAuthStore((s) => s.player);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading, error } = useMyLedger({ page, size: pageSize });

  if (!player) return null;

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div><h1 className="nm-page-title font-bold">Profile</h1><p className="nm-page-subtitle mt-1">Review account state and ledger movement over time.</p></div>

      {/* Account info */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <InfoCard label="Username" value={player.username} />
        <InfoCard
          label="Balance"
          value={`¤ ${formatCurrency(player.balance_micro)}`}
        />
        <InfoCard
          label="Member Since"
          value={new Date(player.created_at).toLocaleDateString()}
        />
      </div>

      {/* Ledger */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            Transaction Ledger
          </h2>
          {data && (
            <span className="text-xs text-gray-500">{data.total} entries</span>
          )}
        </div>

        {isLoading && <LoadingSpinner />}
        {error && <ErrorAlert message="Failed to load ledger" />}
        {data && data.items.length === 0 && (
          <EmptyState message="No transactions yet" />
        )}

        {data && data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="py-2 pr-3">Tick</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Direction</th>
                  <th className="py-2 pr-3">Amount</th>
                  <th className="py-2 pr-3">Memo</th>
                  <th className="py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((entry) => {
                  const isCredit = entry.credit_id === player.id;
                  return (
                    <tr key={entry.id} className="border-b border-gray-800/50">
                      <td className="py-2 pr-3 text-gray-400 text-xs">
                        {entry.tick_id != null ? `#${entry.tick_id}` : "—"}
                      </td>
                      <td className="py-2 pr-3">
                        <span className="text-xs bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded">
                          {entry.entry_type}
                        </span>
                      </td>
                      <td className="py-2 pr-3">
                        <span
                          className={
                            isCredit ? "text-green-400" : "text-red-400"
                          }
                        >
                          {isCredit ? "IN" : "OUT"}
                        </span>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        <span
                          className={
                            isCredit ? "text-green-400" : "text-red-400"
                          }
                        >
                          {isCredit ? "+" : "-"}¤{" "}
                          {formatCurrency(entry.amount_micro)}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-gray-500 text-xs max-w-[200px] truncate">
                        {entry.memo || "—"}
                      </td>
                      <td className="py-2 text-gray-400 text-xs">
                        {formatDate(entry.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

