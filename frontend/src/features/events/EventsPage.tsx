import { useState } from "react";
import { useEvents } from "../../hooks/queries";
import { formatDate } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import { SeverityBadge, Badge } from "../../components/StatusBadge";

const EVENT_TYPES = [
  "",
  "STABILITY_SURGE",
  "STABILITY_CRISIS",
  "YIELD_BOOM",
  "MARKET_SHOCK",
  "DISCOVERY_SURGE",
] as const;

const PAGE_SIZE = 20;

export default function EventsPage() {
  const [eventType, setEventType] = useState("");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;

  const { data, isLoading, error } = useEvents({
    limit: PAGE_SIZE,
    offset,
    event_type: eventType || undefined,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div>
        <h1 className="nm-page-title font-bold">World Events</h1>
        <p className="nm-page-subtitle mt-1">
          Track shocks and temporary modifiers that influence gate and market behavior.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={eventType}
          onChange={(e) => {
            setEventType(e.target.value);
            setPage(1);
          }}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm
                     focus:outline-none focus:border-brand-500"
        >
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t ? t.replace(/_/g, " ") : "All Types"}
            </option>
          ))}
        </select>
        {data && (
          <span className="nm-soft-note">
            {data.total} event{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorAlert message="Failed to load events" />}
      {data && data.items.length === 0 && (
        <EmptyState message="No events recorded yet for this filter." />
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((event) => (
            <div
              key={event.id}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <Badge
                  label={event.event_type.replace(/_/g, " ")}
                  variant="purple"
                />
                <SeverityBadge severity={event.severity} />
                {event.target_type && <Badge label={event.target_type} variant="gray" />}
                <span className="text-xs text-gray-500 ml-auto">
                  Tick #{event.tick_id} - {formatDate(event.created_at)}
                </span>
              </div>

              {event.effects && Object.keys(event.effects).length > 0 && (
                <div className="text-xs text-gray-400 mt-1 space-x-3">
                  {Object.entries(event.effects).map(([k, v]) => (
                    <span key={k}>
                      <span className="text-gray-500">{k}:</span>{" "}
                      {typeof v === "number" ? v.toFixed(2) : String(v)}
                    </span>
                  ))}
                </div>
              )}

              {event.duration_ticks && (
                <div className="text-xs text-gray-500 mt-1">
                  Duration: {event.duration_ticks} ticks
                  {event.expires_at_tick && ` - Expires at tick #${event.expires_at_tick}`}
                </div>
              )}
            </div>
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
