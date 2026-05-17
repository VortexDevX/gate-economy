import { useState } from "react";
import { Link } from "react-router-dom";
import { useGuilds } from "../../hooks/queries";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import { Badge } from "../../components/StatusBadge";
import { formatCurrency, formatPercent, shortId } from "../../utils/format";

const STATUSES = ["", "ACTIVE", "INSOLVENT", "DISSOLVED"] as const;
const PAGE_SIZE = 20;

const statusColors: Record<string, "green" | "amber" | "red" | "gray"> = {
  ACTIVE: "green",
  INSOLVENT: "amber",
  DISSOLVED: "red",
};

export default function GuildsListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const offset = (page - 1) * PAGE_SIZE;
  const { data, isLoading, error } = useGuilds({
    status: statusFilter || undefined,
    offset,
    limit: PAGE_SIZE,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div><h1 className="nm-page-title font-bold">Guilds</h1><p className="nm-page-subtitle mt-1">Track guild treasury health, float policy, and share-market readiness.</p></div>
        <Link
          to="/guilds/create"
          className="bg-brand-600 hover:bg-brand-500 text-white text-sm px-3 py-1.5 rounded"
        >
          Found Guild
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3">
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
        {data && (
          <span className="text-sm text-gray-400">
            {data.total} guild{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorAlert message="Failed to load guilds" />}
      {data && data.guilds.length === 0 && (
        <EmptyState message="No guilds match the current filters." />
      )}

      {data && data.guilds.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Treasury</th>
                <th className="py-2 pr-4">Float</th>
                <th className="py-2 pr-4">Dividend Policy</th>
                <th className="py-2 pr-4">Created</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data.guilds.map((guild) => (
                <tr
                  key={guild.id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50"
                >
                  <td className="py-2.5 pr-4">
                    <div className="font-medium text-gray-200">{guild.name}</div>
                    <div className="font-mono text-xs text-gray-500">
                      {shortId(guild.id)}
                    </div>
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge
                      label={guild.status}
                      variant={statusColors[guild.status] || "gray"}
                    />
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs">
                    {formatCurrency(guild.treasury_micro)}
                  </td>
                  <td className="py-2.5 pr-4">
                    {formatPercent(guild.public_float_pct)}
                  </td>
                  <td className="py-2.5 pr-4">{guild.dividend_policy}</td>
                  <td className="py-2.5 pr-4 text-gray-400">
                    Tick #{guild.created_at_tick}
                  </td>
                  <td className="py-2.5 text-right">
                    <Link
                      to={`/guilds/${guild.id}`}
                      className="text-brand-400 hover:text-brand-300 text-xs"
                    >
                      View
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

