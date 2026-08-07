import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  CalendarPlus,
  CalendarX,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Database,
  FileSearch,
  Flame,
  Gauge,
  Pause,
  Play,
  Save,
  ShieldCheck,
  ShieldX,
  SlidersHorizontal,
  Sparkles,
  Vault,
} from "lucide-react";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import { Badge } from "../../components/StatusBadge";
import {
  GameButton,
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
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
  const { data: parameters, isLoading: paramsLoading, error: paramsError } = useAdminParameters();
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
  const adminActionPending = pause.isPending || resume.isPending || manageSeason.isPending;
  const statusLabel = sim?.is_paused ? "Paused" : sim?.is_running ? "Running" : "Stopped";
  const statusVariant = sim?.is_paused ? "amber" : sim?.is_running ? "green" : "red";
  const statusTone = sim?.is_paused ? "warn" : sim?.is_running ? "good" : "danger";

  const submitParam = async (e: FormEvent, key: string) => {
    e.preventDefault();
    const value = paramDrafts[key];
    if (!value?.trim()) return;
    await patchParam.mutateAsync({ key, value: value.trim() });
  };

  return (
    <div className="game-page admin-command-page grid gap-[18px]">
      <ScreenHeader
        eyebrow="World engine · Privileged command deck"
        title="Simulation Control"
        description="Operate world cycles, launch seasons and events, tune live rules, and verify that every coin remains accounted for. Commands here affect every player."
      />

      <div className="admin-command-warning flex items-start gap-3 border border-amber-800 bg-amber-900/15 p-3 text-sm text-amber-100">
        <AlertTriangle size={19} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span>Administrative actions change the shared realm. Check the current tick and conservation audit before intervening.</span>
      </div>

      <section className="admin-command-stats grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4" aria-label="World engine status">
        <StatRune
          label="World engine"
          value={statusLabel}
          note={`Current cycle ${sim?.current_tick ?? 0}`}
          tone={statusTone}
          icon={<Activity size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Treasury"
          value={`¤ ${formatCurrency(treasury?.balance_micro ?? 0)}`}
          note="System coin available to the economy"
          tone="gold"
          icon={<Vault size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Coin conservation"
          value={audit?.status ?? "Unknown"}
          note={audit ? `Ledger delta ¤ ${formatCurrency(Math.abs(audit.delta_micro))}` : "Audit response not yet available"}
          tone={audit?.status === "PASS" ? "good" : "danger"}
          icon={audit?.status === "PASS" ? <ShieldCheck size={18} aria-hidden="true" /> : <ShieldX size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Last completed cycle"
          value={sim?.last_completed_at ? formatDate(sim.last_completed_at) : "Never"}
          note={sim?.is_running ? "Engine reports active processing" : "No active worker heartbeat reported"}
          tone="aether"
          icon={<Clock3 size={18} aria-hidden="true" />}
        />
      </section>

      <PlainTip>
        Pause stops future cycle resolution; it does not erase queued player commands. Resume only after checking the ledger and active season state.
      </PlainTip>

      <div className="admin-command-controls grid grid-cols-1 gap-4 xl:grid-cols-3">
        <GamePanel className="admin-command-engine p-5" accent={statusTone}>
          <PanelHeading
            title="Engine controls"
            detail="Pause or resume resolution of every queued player command."
            action={<Badge label={statusLabel} variant={statusVariant} />}
          />
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            <GameButton
              tone="danger"
              onClick={() => pause.mutate()}
              disabled={adminActionPending}
              className="w-full"
            >
              <Pause size={16} aria-hidden="true" />
              {pause.isPending ? "Pausing world…" : "Pause cycles"}
            </GameButton>
            <GameButton
              tone="secondary"
              onClick={() => resume.mutate()}
              disabled={adminActionPending}
              className="w-full"
            >
              <Play size={16} aria-hidden="true" />
              {resume.isPending ? "Resuming world…" : "Resume cycles"}
            </GameButton>
          </div>
          <p className="mt-3 text-xs text-[var(--muted)]">
            Pause before rule changes or incident review. Resume processes commands waiting in the player action ledger.
          </p>
          {(pause.error || resume.error) && (
            <div className="mt-3"><ErrorAlert message="The engine command failed. Confirm worker and API health before retrying." /></div>
          )}
        </GamePanel>

        <GamePanel className="admin-command-season p-5" accent="violet">
          <PanelHeading
            title="Season lifecycle"
            detail="Open a new competitive record or close the current one."
            action={<Gauge size={19} className="tone-violet" aria-hidden="true" />}
          />
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            <GameButton
              onClick={() => manageSeason.mutate({ action: "create" })}
              disabled={adminActionPending}
              className="w-full"
            >
              <CalendarPlus size={16} aria-hidden="true" />
              {manageSeason.isPending ? "Applying…" : "Create season"}
            </GameButton>
            <GameButton
              tone="danger"
              onClick={() => manageSeason.mutate({ action: "end" })}
              disabled={adminActionPending}
              className="w-full"
            >
              <CalendarX size={16} aria-hidden="true" />
              {manageSeason.isPending ? "Applying…" : "End season"}
            </GameButton>
          </div>
          <p className="mt-3 text-xs text-[var(--muted)]">
            Ending a season finalizes its competitive window. Creation starts a new world ranking period.
          </p>
          {manageSeason.error && (
            <div className="mt-3"><ErrorAlert message="The season command failed. The existing season state was not intentionally changed." /></div>
          )}
          {manageSeason.isSuccess && (
            <div className="mt-3 flex items-start gap-2 border border-green-800 bg-green-900/20 p-2 text-xs text-green-300" role="status">
              <CheckCircle2 size={16} className="shrink-0" aria-hidden="true" />
              <span>{manageSeason.data?.message}</span>
            </div>
          )}
        </GamePanel>

        <GamePanel className="admin-command-event p-5" accent="warn">
          <PanelHeading
            title="World event"
            detail="Queue one realm-wide modifier for the simulation engine."
            action={<Flame size={19} className="tone-warn" aria-hidden="true" />}
          />
          <label htmlFor="admin-event-type" className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
            Event effect
          </label>
          <select
            id="admin-event-type"
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="mt-1.5 min-h-11 w-full px-3 py-2 text-sm"
          >
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {plainEventName(type)}
              </option>
            ))}
          </select>
          <GameButton
            onClick={() => triggerEvent.mutate(eventType)}
            disabled={triggerEvent.isPending}
            className="mt-3 w-full"
          >
            <Sparkles size={16} aria-hidden="true" />
            {triggerEvent.isPending ? "Queueing event…" : "Queue world event"}
          </GameButton>
          <p className="mt-3 text-xs text-[var(--muted)]">The event enters the world engine and affects the shared economy when processed.</p>
          {triggerEvent.error && (
            <div className="mt-3"><ErrorAlert message="The world event could not be queued." /></div>
          )}
          {triggerEvent.isSuccess && (
            <div className="mt-3 flex items-start gap-2 border border-green-800 bg-green-900/20 p-2 text-xs text-green-300" role="status">
              <CheckCircle2 size={16} className="shrink-0" aria-hidden="true" />
              <span>Queued: {plainEventName(triggerEvent.data?.event_type ?? eventType)}</span>
            </div>
          )}
        </GamePanel>
      </div>

      <GamePanel className="admin-command-parameters p-5" accent="aether">
        <PanelHeading
          title="Live rule parameters"
          detail="Edit one engine value at a time. Bounds are validated by the server; changes affect future world calculations."
          action={<SlidersHorizontal size={19} className="tone-aether" aria-hidden="true" />}
        />
        {paramsLoading && <LoadingSpinner />}
        {paramsError && <ErrorAlert message="Live simulation parameters could not be loaded." />}
        {patchParam.error && (
          <ErrorAlert message="The parameter update failed. Check the expected type and server bounds before retrying." />
        )}
        {!paramsLoading && !paramsError && paramRows.length === 0 && (
          <GameEmpty title="No live parameters exposed" message="The API returned no editable simulation rules." />
        )}
        {!paramsLoading && paramRows.length > 0 && (
          <div className="admin-command-table overflow-x-auto">
            <table className="min-w-[920px] text-sm">
              <thead>
                <tr className="border-b border-[var(--line)] text-left">
                  <th className="py-3 pr-4">Rule</th>
                  <th className="py-3 pr-4">Current</th>
                  <th className="py-3 pr-4">Type</th>
                  <th className="py-3 pr-4">Replacement value</th>
                  <th className="py-3">Last changed</th>
                </tr>
              </thead>
              <tbody>
                {paramRows.map((parameter) => (
                  <tr key={parameter.key} className="border-b border-[var(--line)] align-top">
                    <td className="py-3 pr-4">
                      <strong className="block font-mono text-xs text-[var(--parchment)]">{parameter.key}</strong>
                      {parameter.description && <small className="mt-1 block max-w-xs text-[10px] text-[var(--muted)]">{parameter.description}</small>}
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs">{parameter.value}</td>
                    <td className="py-3 pr-4"><span className="game-badge">{parameter.value_type}</span></td>
                    <td className="py-3 pr-4">
                      <form onSubmit={(e) => submitParam(e, parameter.key)} className="flex min-w-[260px] items-center gap-2">
                        <label htmlFor={`admin-param-${parameter.key}`} className="sr-only">New value for {parameter.key}</label>
                        <input
                          id={`admin-param-${parameter.key}`}
                          value={paramDrafts[parameter.key] ?? ""}
                          onChange={(e) => setParamDrafts((previous) => ({ ...previous, [parameter.key]: e.target.value }))}
                          className="min-h-9 min-w-0 flex-1 px-2 py-1 font-mono text-xs"
                          placeholder={parameter.value}
                          autoComplete="off"
                        />
                        <GameButton type="submit" tone="secondary" disabled={patchParam.isPending || !(paramDrafts[parameter.key]?.trim())}>
                          <Save size={14} aria-hidden="true" />
                          {patchParam.isPending ? "Saving…" : "Apply"}
                        </GameButton>
                      </form>
                    </td>
                    <td className="py-3 text-xs text-[var(--muted)]">{formatDate(parameter.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GamePanel>

      <section className="admin-command-audit grid grid-cols-1 gap-4 xl:grid-cols-[.75fr_1.25fr]" aria-label="Economy audit">
        <GamePanel className="admin-command-conservation p-5" accent={audit?.status === "PASS" ? "good" : "danger"}>
          <PanelHeading
            title="Conservation ledger"
            detail="Every coin should be held by the treasury, a player, or a guild."
            action={audit?.status === "PASS"
              ? <ShieldCheck size={20} className="tone-good" aria-hidden="true" />
              : <ShieldX size={20} className="tone-danger" aria-hidden="true" />}
          />
          {!audit ? (
            <LoadingSpinner />
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2" aria-label="Coin conservation totals">
              <AuditRow icon={<Vault />} label="Treasury" value={`¤ ${formatCurrency(audit.treasury_balance_micro)}`} />
              <AuditRow icon={<CircleDollarSign />} label="Player balances" value={`¤ ${formatCurrency(audit.player_sum_micro)}`} />
              <AuditRow icon={<Database />} label="Guild treasuries" value={`¤ ${formatCurrency(audit.guild_sum_micro)}`} />
              <AuditRow icon={<ArrowRightLeft />} label="Expected total" value={`¤ ${formatCurrency(audit.expected_micro)}`} />
              <AuditRow icon={<FileSearch />} label="Actual total" value={`¤ ${formatCurrency(audit.total_micro)}`} />
              <AuditRow
                icon={audit.status === "PASS" ? <ShieldCheck /> : <AlertTriangle />}
                label="Unaccounted delta"
                value={`¤ ${formatCurrency(audit.delta_micro)}`}
                tone={audit.status === "PASS" ? "good" : "danger"}
              />
            </div>
          )}
        </GamePanel>

        <GamePanel className="admin-command-treasury-ledger p-5" accent="gold">
          <PanelHeading
            title="Recent treasury movements"
            detail="The latest debits and credits involving the system treasury."
            action={<Vault size={19} className="tone-gold" aria-hidden="true" />}
          />
          {!treasury && <LoadingSpinner />}
          {treasury && treasury.recent_entries.length === 0 && (
            <GameEmpty title="No treasury movements" message="No recent treasury ledger entries were returned." />
          )}
          {treasury && treasury.recent_entries.length > 0 && (
            <ul className="admin-command-ledger-list grid max-h-80 gap-2 overflow-auto pr-1">
              {treasury.recent_entries.slice(0, 12).map((entry) => (
                <li key={entry.id} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border border-[var(--line)] bg-black/10 p-3 text-xs">
                  <span className="font-mono text-[var(--muted)]">#{entry.id}</span>
                  <div className="min-w-0">
                    <strong className="block truncate text-[var(--parchment-soft)]">{plainLedgerName(entry.entry_type)}</strong>
                    <small className="text-[10px] text-[var(--muted)]">{entry.tick_id == null ? "Outside a world cycle" : `Cycle ${entry.tick_id}`}</small>
                  </div>
                  <strong className="font-mono tone-gold">¤ {formatCurrency(entry.amount_micro)}</strong>
                </li>
              ))}
            </ul>
          )}
        </GamePanel>
      </section>

      <GamePanel className="admin-command-global-ledger p-5" accent="muted">
        <PanelHeading
          title="Global ledger browser"
          detail="The newest transfers across treasury, player, and guild accounts."
          action={<Database size={19} className="text-[var(--muted)]" aria-hidden="true" />}
        />
        {!ledger && <LoadingSpinner />}
        {ledger && ledger.length === 0 && (
          <GameEmpty title="No global transfers" message="The ledger API returned no entries for this window." />
        )}
        {ledger && ledger.length > 0 && (
          <ol className="admin-command-global-list grid grid-cols-1 gap-2 lg:grid-cols-2" aria-label="Recent global ledger entries">
            {ledger.map((entry) => (
              <li key={entry.id} className="admin-command-global-entry grid gap-2 border border-[var(--line)] bg-black/10 p-3 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <span className="game-badge">Ledger #{entry.id}</span>
                  <span className="text-[var(--muted)]">{entry.tick_id == null ? "No cycle" : `Cycle ${entry.tick_id}`}</span>
                </div>
                <strong className="font-mono text-[var(--parchment-soft)]">
                  {shortId(entry.debit_id)} <ArrowRight className="tone-aether inline-icon" size={13} aria-hidden="true" /> {shortId(entry.credit_id)}
                </strong>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[var(--muted)]">{plainLedgerName(entry.entry_type)}</span>
                  <strong className="font-mono tone-gold">¤ {formatCurrency(entry.amount_micro)}</strong>
                </div>
              </li>
            ))}
          </ol>
        )}
      </GamePanel>
    </div>
  );
}

function AuditRow({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone?: "good" | "danger";
}) {
  return (
    <div className="admin-command-audit-row grid grid-cols-[26px_1fr] gap-x-2 border border-[var(--line)] bg-black/10 p-3">
      <span className={`row-span-2 ${tone ? `tone-${tone}` : "tone-aether"}`} aria-hidden="true">{icon}</span>
      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{label}</span>
      <strong className="mt-0.5 font-mono text-sm text-[var(--parchment-soft)]">{value}</strong>
    </div>
  );
}

function plainEventName(value: string): string {
  const names: Record<string, string> = {
    STABILITY_SURGE: "Stability surge — safer gates",
    STABILITY_CRISIS: "Stability crisis — dangerous gates",
    YIELD_BOOM: "Yield boom — stronger payouts",
    MARKET_SHOCK: "Market shock — trading disruption",
    DISCOVERY_SURGE: "Discovery surge — more gate activity",
  };
  return names[value] ?? sentenceCase(value);
}

function plainLedgerName(value: string): string {
  return sentenceCase(value);
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
