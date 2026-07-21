import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CloudLightning,
  Compass,
  Radio,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Waves,
  type LucideIcon,
} from "lucide-react";
import type { EventResponse } from "../../api/types";
import {
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import Pagination from "../../components/Pagination";
import { useEvents } from "../../hooks/queries";
import { formatDate, shortId } from "../../utils/format";

const EVENT_TYPES = [
  "",
  "STABILITY_SURGE",
  "STABILITY_CRISIS",
  "YIELD_BOOM",
  "MARKET_SHOCK",
  "DISCOVERY_SURGE",
] as const;
const PAGE_SIZE = 20;

const omenPresentation: Record<
  string,
  { title: string; short: string; copy: string; icon: LucideIcon; tone: string }
> = {
  "": {
    title: "Every omen",
    short: "All",
    copy: "All world forces",
    icon: Radio,
    tone: "violet",
  },
  STABILITY_SURGE: {
    title: "Stabilizing Tide",
    short: "Safer gates",
    copy: "Gate safety is being strengthened",
    icon: ShieldCheck,
    tone: "good",
  },
  STABILITY_CRISIS: {
    title: "Collapse Storm",
    short: "Gate danger",
    copy: "Gate safety is under pressure",
    icon: CloudLightning,
    tone: "danger",
  },
  YIELD_BOOM: {
    title: "Mana Harvest",
    short: "More income",
    copy: "Gate earnings are being amplified",
    icon: TrendingUp,
    tone: "gold",
  },
  MARKET_SHOCK: {
    title: "Market Rupture",
    short: "Price shock",
    copy: "Trading conditions are disrupted",
    icon: Waves,
    tone: "warn",
  },
  DISCOVERY_SURGE: {
    title: "Open Paths",
    short: "Discovery boost",
    copy: "Expeditions have favorable conditions",
    icon: Compass,
    tone: "aether",
  },
};

export default function EventsPage() {
  const [eventType, setEventType] = useState("");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const eventsQuery = useEvents({
    limit: PAGE_SIZE,
    offset,
    event_type: eventType || undefined,
  });

  const events = eventsQuery.data?.items ?? [];
  const totalPages = eventsQuery.data
    ? Math.ceil(eventsQuery.data.total / PAGE_SIZE)
    : 0;

  return (
    <div className="game-page omen-page">
      <ScreenHeader
        eyebrow="Active omens · World forces"
        title="Read the Weather of the Realm"
        description="Omens temporarily change how gates, expeditions, and markets behave. Check duration and affected targets before making your next move."
      />

      <GamePanel className="omen-filter-panel" accent="violet">
        <PanelHeading
          title="Which force matters to you?"
          detail="Filter the record to the risk or opportunity you are watching."
          action={eventsQuery.data && (
            <span className="omen-count">
              {eventsQuery.data.total} omen{eventsQuery.data.total === 1 ? "" : "s"}
            </span>
          )}
        />
        <div className="omen-filters" role="group" aria-label="Filter world omens">
          {EVENT_TYPES.map((value) => {
            const presentation = omenPresentation[value];
            const Icon = presentation.icon;
            return (
              <button
                key={value || "ALL"}
                type="button"
                onClick={() => {
                  setEventType(value);
                  setPage(1);
                }}
                className={`omen-filter omen-tone-${presentation.tone} ${eventType === value ? "is-active" : ""}`}
                aria-pressed={eventType === value}
              >
                <Icon size={18} aria-hidden="true" />
                <span>
                  <strong>{presentation.short}</strong>
                  <small>{presentation.copy}</small>
                </span>
              </button>
            );
          })}
        </div>
      </GamePanel>

      <PlainTip>
        An omen is a temporary modifier, not a permanent rule. Its duration tells you how many world cycles remain relevant to your decision.
      </PlainTip>

      {eventsQuery.isLoading && <LoadingSpinner />}
      {eventsQuery.error && (
        <ErrorAlert message="The omen record could not be read. Your gates and orders remain unchanged." />
      )}
      {!eventsQuery.isLoading && !eventsQuery.error && events.length === 0 && (
        <GamePanel className="omen-empty-panel" accent="muted">
          <GameEmpty
            title={eventType ? "No omen of this kind" : "The realm is calm"}
            message={eventType
              ? "Choose another force or wait for later world cycles."
              : "No world-wide force has been recorded yet. Normal gate and market rules still apply."}
            action={{ to: "/news", label: "Read world dispatches" }}
          />
        </GamePanel>
      )}

      {events.length > 0 && (
        <section className="omen-grid" aria-label="Recorded world omens">
          {events.map((event) => (
            <OmenCard key={event.id} event={event} />
          ))}
        </section>
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

function OmenCard({ event }: { event: EventResponse }) {
  const presentation = omenPresentation[event.event_type] ?? {
    title: sentenceCase(event.event_type),
    short: sentenceCase(event.event_type),
    copy: "A world force is in effect",
    icon: Sparkles,
    tone: "violet",
  };
  const Icon = presentation.icon;
  const destination = relatedDestination(event);

  return (
    <GamePanel className={`omen-card omen-tone-${presentation.tone}`} accent={panelTone(presentation.tone)}>
      <div className="omen-card-head">
        <span className="omen-sigil"><Icon size={28} aria-hidden="true" /></span>
        <div>
          <span className="omen-severity">{plainSeverity(event.severity)}</span>
          <h2>{presentation.title}</h2>
          <p>{presentation.copy}</p>
        </div>
      </div>

      <div className="omen-timing">
        <span><Activity size={15} aria-hidden="true" /> Began in cycle {event.tick_number ?? event.tick_id}</span>
        {event.duration_ticks != null && (
          <span><Radio size={15} aria-hidden="true" /> Lasts {event.duration_ticks} cycle{event.duration_ticks === 1 ? "" : "s"}</span>
        )}
        {event.expires_at_tick != null && (
          <span><AlertTriangle size={15} aria-hidden="true" /> Scheduled through cycle {event.expires_at_tick}</span>
        )}
      </div>

      {event.effects && Object.keys(event.effects).length > 0 && (
        <dl className="omen-effects">
          {Object.entries(event.effects).map(([key, value]) => (
            <div key={key}>
              <dt>{plainEffectName(key)}</dt>
              <dd>{plainEffectValue(key, value)}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="omen-card-foot">
        <span>
          {event.target_type
            ? `Affects ${plainTarget(event.target_type)}${event.target_id ? ` ${shortId(event.target_id)}` : ""}`
            : "Affects the whole realm"}
        </span>
        <time dateTime={event.created_at}>{formatDate(event.created_at)}</time>
        {destination && (
          <Link to={destination}>
            Inspect target <ArrowRight size={14} aria-hidden="true" />
          </Link>
        )}
      </div>
    </GamePanel>
  );
}

function plainSeverity(severity: string): string {
  const labels: Record<string, string> = {
    MINOR: "Low impact",
    MODERATE: "Worth watching",
    MAJOR: "High impact",
    CATASTROPHIC: "Realm-wide danger",
  };
  return labels[severity] ?? sentenceCase(severity);
}

function plainEffectName(key: string): string {
  const labels: Record<string, string> = {
    stability_delta: "Stability change",
    stability_multiplier: "Stability strength",
    yield_delta: "Income change",
    yield_multiplier: "Income strength",
    volatility_delta: "Market volatility",
    volatility_multiplier: "Volatility strength",
    discovery_multiplier: "Discovery chance",
    discovery_chance_multiplier: "Discovery chance",
    price_multiplier: "Price pressure",
  };
  return labels[key] ?? sentenceCase(key);
}

function plainEffectValue(key: string, value: unknown): string {
  if (typeof value !== "number") return String(value);
  if (key.includes("multiplier")) return `×${value.toFixed(2)}`;
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number.isInteger(value) ? value : value.toFixed(2)}`;
}

function plainTarget(target: string): string {
  const labels: Record<string, string> = {
    GATE: "gate",
    GUILD: "guild",
    MARKET: "the market",
    WORLD: "the whole realm",
    ALL_GATES: "all gates",
  };
  return labels[target] ?? target.replace(/_/g, " ").toLowerCase();
}

function relatedDestination(event: EventResponse): string | null {
  if (!event.target_id) return null;
  if (event.target_type === "GATE") return `/gates/${event.target_id}`;
  if (event.target_type === "GUILD") return `/guilds/${event.target_id}`;
  return null;
}

function panelTone(tone: string): "gold" | "aether" | "good" | "warn" | "danger" | "violet" | "muted" {
  if (tone === "gold" || tone === "aether" || tone === "good" || tone === "warn" || tone === "danger" || tone === "violet") {
    return tone;
  }
  return "muted";
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
