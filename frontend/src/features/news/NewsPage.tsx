import { useState } from "react";
import { useNews } from "../../hooks/queries";
import { formatDate } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import { Badge } from "../../components/StatusBadge";

const CATEGORIES = [
  "",
  "EVENT",
  "GATE",
  "MARKET",
  "GUILD",
  "LEADERBOARD",
  "WORLD",
] as const;
const PAGE_SIZE = 20;

type Variant =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "orange"
  | "yellow";

const categoryColors: Record<string, Variant> = {
  EVENT: "amber",
  GATE: "purple",
  MARKET: "green",
  GUILD: "blue",
  LEADERBOARD: "orange",
  WORLD: "gray",
};

export default function NewsPage() {
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;

  const { data, isLoading, error } = useNews({
    limit: PAGE_SIZE,
    offset,
    category: category || undefined,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div>
        <h1 className="nm-page-title font-bold">News Feed</h1>
        <p className="nm-page-subtitle mt-1">
          Simulation-generated headlines across markets, guilds, and world events.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm
                     focus:outline-none focus:border-brand-500"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c || "All Categories"}
            </option>
          ))}
        </select>
        {data && (
          <span className="nm-soft-note">
            {data.total} article{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorAlert message="Failed to load news" />}
      {data && data.items.length === 0 && (
        <EmptyState message="No headlines yet. Let a few ticks run and this feed will populate." />
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((news) => (
            <article
              key={news.id}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <Badge
                  label={news.category}
                  variant={categoryColors[news.category] || "gray"}
                />
                <ImportanceDots value={news.importance} />
                <span className="text-xs text-gray-500 ml-auto">
                  Tick #{news.tick_id} - {formatDate(news.created_at)}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-gray-100">{news.headline}</h3>
              {news.body && <p className="text-xs text-gray-400 mt-1">{news.body}</p>}
            </article>
          ))}
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

function ImportanceDots({ value }: { value: number }) {
  return (
    <span className="flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < value ? "bg-brand-400" : "bg-gray-700"}`}
        />
      ))}
    </span>
  );
}
