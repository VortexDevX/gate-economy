import { useMemo, useState, type FormEvent } from "react";
import {
  useAdminLedger,
  useAdminParameters,
  useAdminTreasury,
  useConservationAudit,
  useManageSeason,
  usePatchAdminParameter,
  usePauseSimulation,
  useResumeSimulation,
  useSimulationStatus,
  useTriggerAdminEvent,
} from "../../hooks/queries";
import { formatCurrency, formatDate, shortId } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import { Badge } from "../../components/StatusBadge";

const EVENT_TYPES = [
  "STABILITY_SURGE",
  "STABILITY_CRISIS",
  "YIELD_BOOM",
  "MARKET_SHOCK",
  "DISCOVERY_SURGE",
];

export default function AdminPage() {
  const { data: sim } = useSimulationStatus();
  const { data: treasury } = useAdminTreasury();
  const { data: parameters, isLoading: paramsLoading, error: paramsError } =
    useAdminParameters();
  const { data: audit } = useConservationAudit();
  const { data: ledger } = useAdminLedger({ limit: 50, offset: 0 });

  const pause = usePauseSimulation();
  const resume = useResumeSimulation();
  const patchParam = usePatchAdminParameter();
  const triggerEvent = useTriggerAdminEvent();
  const manageSeason = useManageSeason();

  const [eventType, setEventType] = useState(EVENT_TYPES[0]);
  const [paramDrafts, setParamDrafts] = useState<Record<string, string>>({});

  const paramRows = useMemo(() => parameters ?? [], [parameters]);

  const statusLabel = sim?.is_paused
    ? "Paused"
    : sim?.is_running
      ? "Running"
      : "Stopped";
  const statusVariant = sim?.is_paused
    ? "amber"
    : sim?.is_running
      ? "green"
      : "red";

  const submitParam = async (e: FormEvent, key: string) => {
    e.preventDefault();
    const value = paramDrafts[key];
    if (!value?.trim()) return;
    await patchParam.mutateAsync({ key, value: value.trim() });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <div>
        <h1 className="nm-page-title font-bold">Admin Control Center</h1>
        <p className="nm-page-subtitle mt-1">
          Simulation operations, tuning, audit checks, and season controls.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card label="Simulation Status">
          <div className="flex items-center gap-2">
            <Badge label={statusLabel} variant={statusVariant} />
            <span className="text-xs text-gray-500">Tick #{sim?.current_tick ?? 0}</span>
          </div>
        </Card>
        <Card label="Treasury Balance">
          <span className="font-mono">¤ {formatCurrency(treasury?.balance_micro ?? 0)}</span>
        </Card>
        <Card label="Conservation Audit">
          <Badge label={audit?.status ?? "UNKNOWN"} variant={audit?.status === "PASS" ? "green" : "red"} />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="nm-card rounded-xl p-4 space-y-3">
          <h2 className="nm-panel-title">Simulation Controls</h2>
          <div className="flex gap-3">
            <button
              onClick={() => pause.mutate()}
              disabled={pause.isPending}
              className="bg-amber-600 hover:bg-amber-500 text-white text-sm px-4 py-2 rounded"
            >
              Pause
            </button>
            <button
              onClick={() => resume.mutate()}
              disabled={resume.isPending}
              className="bg-brand-600 hover:bg-brand-500 text-white text-sm px-4 py-2 rounded"
            >
              Resume
            </button>
            <button
              onClick={() => manageSeason.mutate({ action: "create" })}
              className="bg-gray-900 text-sm px-4 py-2 rounded border border-gray-700"
            >
              Create Season
            </button>
            <button
              onClick={() => manageSeason.mutate({ action: "end" })}
              className="bg-gray-900 text-sm px-4 py-2 rounded border border-gray-700"
            >
              End Season
            </button>
          </div>
          {(pause.error || resume.error || manageSeason.error) && (
            <ErrorAlert message="Admin simulation action failed." />
          )}
        </section>

        <section className="nm-card rounded-xl p-4 space-y-3">
          <h2 className="nm-panel-title">Event Trigger</h2>
          <div className="flex gap-2">
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
            >
              {EVENT_TYPES.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
            <button
              onClick={() => triggerEvent.mutate(eventType)}
              disabled={triggerEvent.isPending}
              className="bg-brand-600 hover:bg-brand-500 text-white text-sm px-4 py-2 rounded"
            >
              Trigger
            </button>
          </div>
          {triggerEvent.isSuccess && (
            <div className="nm-soft-note">
              Event queued: {triggerEvent.data?.event_type}
            </div>
          )}
        </section>
      </div>

      <section className="nm-card rounded-xl p-4">
        <h2 className="nm-panel-title mb-3">Parameters</h2>
        {paramsLoading && <LoadingSpinner />}
        {paramsError && <ErrorAlert message="Failed to load parameters." />}
        {!paramsLoading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-800">
                  <th className="py-2 pr-3">Key</th>
                  <th className="py-2 pr-3">Current Value</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">New Value</th>
                  <th className="py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {paramRows.map((p) => (
                  <tr key={p.key} className="border-b border-gray-800/50">
                    <td className="py-2 pr-3 font-mono text-xs">{p.key}</td>
                    <td className="py-2 pr-3 font-mono">{p.value}</td>
                    <td className="py-2 pr-3">{p.value_type}</td>
                    <td className="py-2 pr-3">
                      <form
                        onSubmit={(e) => submitParam(e, p.key)}
                        className="flex items-center gap-2"
                      >
                        <input
                          value={paramDrafts[p.key] ?? ""}
                          onChange={(e) =>
                            setParamDrafts((prev) => ({
                              ...prev,
                              [p.key]: e.target.value,
                            }))
                          }
                          className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs"
                        />
                        <button
                          type="submit"
                          className="text-xs px-2 py-1 rounded bg-brand-600 text-white"
                        >
                          Save
                        </button>
                      </form>
                    </td>
                    <td className="py-2 text-xs text-gray-500">
                      {formatDate(p.updated_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="nm-card rounded-xl p-4">
          <h2 className="nm-panel-title mb-3">Treasury Ledger (Recent)</h2>
          {!treasury && <LoadingSpinner />}
          {treasury && treasury.recent_entries.length === 0 && (
            <div className="nm-soft-note">No treasury entries found.</div>
          )}
          {treasury && treasury.recent_entries.length > 0 && (
            <ul className="space-y-2">
              {treasury.recent_entries.slice(0, 12).map((entry) => (
                <li key={entry.id} className="text-xs flex items-center justify-between">
                  <span className="font-mono">#{entry.id}</span>
                  <span>{entry.entry_type}</span>
                  <span className="font-mono">¤ {formatCurrency(entry.amount_micro)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="nm-card rounded-xl p-4">
          <h2 className="nm-panel-title mb-3">Global Ledger Browser</h2>
          {!ledger && <LoadingSpinner />}
          {ledger && ledger.length > 0 && (
            <ul className="space-y-2 max-h-72 overflow-auto pr-1">
              {ledger.map((entry) => (
                <li key={entry.id} className="text-xs border border-gray-800 rounded px-2 py-2">
                  <div className="flex justify-between">
                    <span>#{entry.id}</span>
                    <span>Tick {entry.tick_id ?? "-"}</span>
                  </div>
                  <div className="font-mono mt-1">
                    {shortId(entry.debit_id)} → {shortId(entry.credit_id)}
                  </div>
                  <div className="mt-1">{entry.entry_type} · ¤ {formatCurrency(entry.amount_micro)}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="nm-card rounded-xl p-3">
      <div className="nm-panel-title mb-1">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}
