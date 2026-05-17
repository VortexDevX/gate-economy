import { useState } from "react";
import { Link } from "react-router-dom";
import { useGates } from "../../hooks/queries";
import { formatCurrency, formatStability } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import { GateRankBadge, GateStatusBadge } from "../../components/StatusBadge";

const STATUSES = ["", "OFFERING", "ACTIVE", "UNSTABLE", "COLLAPSED"] as const;
const RANKS = ["", "E", "D", "C", "B", "A", "S", "S_PLUS"] as const;
const PAGE_SIZE = 20;

export default function GatesListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [rankFilter, setRankFilter] = useState("");
  const [page, setPage] = useState(1);

  const offset = (page - 1) * PAGE_SIZE;
  const { data, isLoading, error } = useGates({
    status: statusFilter || undefined,
    rank: rankFilter || undefined,
    offset,
    limit: PAGE_SIZE,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div>
        <h1 className="nm-page-title font-bold">Dungeon Gates</h1>
        <p className="nm-page-subtitle mt-1">
          Filter active opportunities and inspect gate health before trading.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm
                     focus:outline-none focus:border-brand-500"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || "All Statuses"}
            </option>
          ))}
        </select>
        <select
          value={rankFilter}
          onChange={(e) => {
            setRankFilter(e.target.value);
            setPage(1);
          }}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm
                     focus:outline-none focus:border-brand-500"
        >
          {RANKS.map((r) => (
            <option key={r} value={r}>
              {r ? (r === "S_PLUS" ? "S+" : r) : "All Ranks"}
            </option>
          ))}
        </select>
        {data && (
          <span className="nm-soft-note self-center">
            {data.total} gate{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorAlert message="Failed to load gates" />}
      {data && data.gates.length === 0 && (
        <EmptyState message="No gates matched this filter set." />
      )}

      {data && data.gates.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800">
                <th className="py-2 pr-4">Rank</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Stability</th>
                <th className="py-2 pr-4">Yield / tick</th>
                <th className="py-2 pr-4">Shares</th>
                <th className="py-2 pr-4">Spawned</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data.gates.map((gate) => (
                <tr
                  key={gate.id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50"
                >
                  <td className="py-2.5 pr-4">
                    <GateRankBadge rank={gate.rank} />
                  </td>
                  <td className="py-2.5 pr-4">
                    <GateStatusBadge status={gate.status} />
                  </td>
                  <td className="py-2.5 pr-4">
                    <StabilityBar value={gate.stability} />
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs">
                    ¤ {formatCurrency(gate.base_yield_micro)}
                  </td>
                  <td className="py-2.5 pr-4">{gate.total_shares}</td>
                  <td className="py-2.5 pr-4 text-gray-400">
                    Tick #{gate.spawned_at_tick}
                  </td>
                  <td className="py-2.5 text-right">
                    <Link
                      to={`/gates/${gate.id}`}
                      className="text-brand-400 hover:text-brand-300 text-xs"
                    >
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
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
  );
}

function StabilityBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color =
    clamped > 60
      ? "bg-green-500"
      : clamped > 30
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs text-gray-400">{formatStability(value)}</span>
    </div>
  );
}

