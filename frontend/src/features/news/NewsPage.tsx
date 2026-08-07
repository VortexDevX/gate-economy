import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Aperture,
  ArrowRight,
  Crown,
  Newspaper,
  Radio,
  Shield,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import type { NewsResponse } from "../../api/types";
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
import { useNews } from "../../hooks/queries";
import { formatDate } from "../../utils/format";

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

const categoryPresentation: Record<
  string,
  { label: string; icon: LucideIcon; copy: string }
> = {
  "": { label: "All dispatches", icon: Newspaper, copy: "Every signal" },
  EVENT: { label: "World omens", icon: Radio, copy: "Temporary forces" },
  GATE: { label: "Gate reports", icon: Aperture, copy: "Safety and yield" },
  MARKET: { label: "Market moves", icon: TrendingUp, copy: "Price and trade" },
  GUILD: { label: "Guild reports", icon: Shield, copy: "Treasury and policy" },
  LEADERBOARD: { label: "Season reports", icon: Crown, copy: "Rank changes" },
  WORLD: { label: "Realm dispatches", icon: Sparkles, copy: "Global news" },
};

export default function NewsPage() {
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const newsQuery = useNews({
    limit: PAGE_SIZE,
    offset,
    category: category || undefined,
  });

  const items = newsQuery.data?.items ?? [];
  const totalPages = newsQuery.data
    ? Math.ceil(newsQuery.data.total / PAGE_SIZE)
    : 0;
  const lead = items[0];
  const remaining = items.slice(1);

  return (
    <div className="game-page dispatch-page">
      <ScreenHeader
        eyebrow="World dispatches · Read before you act"
        title="News from Beyond the Gates"
        description="Headlines reveal changes in gate safety, income, market appetite, and season pressure. Read the signal, then inspect any holding it could affect."
      />

      <GamePanel className="dispatch-filter-panel" accent="muted">
        <PanelHeading
          title="Choose a signal"
          detail="You never need every headline. Filter to the part of the world you are deciding about."
          action={newsQuery.data && (
            <span className="dispatch-count">
              {newsQuery.data.total} dispatch{newsQuery.data.total === 1 ? "" : "es"}
            </span>
          )}
        />
        <div className="dispatch-filters" role="group" aria-label="Filter world dispatches">
          {CATEGORIES.map((value) => {
            const presentation = categoryPresentation[value];
            const Icon = presentation.icon;
            return (
              <button
                key={value || "ALL"}
                type="button"
                onClick={() => {
                  setCategory(value);
                  setPage(1);
                }}
                className={`dispatch-filter ${category === value ? "is-active" : ""}`}
                aria-pressed={category === value}
              >
                <Icon size={17} aria-hidden="true" />
                <span>
                  <strong>{presentation.label}</strong>
                  <small>{presentation.copy}</small>
                </span>
              </button>
            );
          })}
        </div>
      </GamePanel>

      <PlainTip>
        High-importance dispatches deserve attention, but they are not automatic trade advice. Check the linked gate or guild before spending coin.
      </PlainTip>

      {newsQuery.isLoading && <LoadingSpinner />}
      {newsQuery.error && (
        <ErrorAlert message="The dispatch line is quiet because news could not be loaded. Your holdings and orders are unaffected." />
      )}
      {!newsQuery.isLoading && !newsQuery.error && items.length === 0 && (
        <GamePanel className="dispatch-empty-panel" accent="muted">
          <GameEmpty
            title={category ? "No dispatches match this signal" : "The world has not spoken yet"}
            message={category
              ? "Choose another signal or wait for later world cycles to create new reports."
              : "Once the world advances, gate discoveries, trades, omens, and season changes will be recorded here."}
            action={category ? { to: "/events", label: "Inspect active omens" } : { to: "/guide", label: "Read the field guide" }}
          />
        </GamePanel>
      )}

      {lead && (
        <section className="dispatch-feed" aria-label="World dispatches">
          <LeadDispatch item={lead} />
          {remaining.length > 0 && (
            <div className="dispatch-list">
              {remaining.map((item) => (
                <DispatchCard key={item.id} item={item} />
              ))}
            </div>
          )}
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

function LeadDispatch({ item }: { item: NewsResponse }) {
  const presentation = categoryPresentation[item.category] ?? categoryPresentation.WORLD;
  const Icon = presentation.icon;
  const destination = relatedDestination(item);
  return (
    <GamePanel className={`dispatch-lead dispatch-tone-${item.category.toLowerCase()}`} accent="gold">
      <div className="dispatch-lead-mark"><Icon size={30} aria-hidden="true" /></div>
      <div className="dispatch-lead-copy">
        <div className="dispatch-meta">
          <span>{presentation.label}</span>
          <Importance value={item.importance} />
          <time dateTime={item.created_at}>
            Cycle {item.tick_number ?? item.tick_id} · {formatDate(item.created_at)}
          </time>
        </div>
        <h2>{item.headline}</h2>
        {item.body && <p>{item.body}</p>}
        {destination && (
          <Link to={destination} className="dispatch-related-link">
            Inspect what this may affect <ArrowRight size={15} aria-hidden="true" />
          </Link>
        )}
      </div>
    </GamePanel>
  );
}

function DispatchCard({ item }: { item: NewsResponse }) {
  const presentation = categoryPresentation[item.category] ?? categoryPresentation.WORLD;
  const Icon = presentation.icon;
  const destination = relatedDestination(item);
  return (
    <article className={`dispatch-card dispatch-tone-${item.category.toLowerCase()}`}>
      <div className="dispatch-card-icon"><Icon size={20} aria-hidden="true" /></div>
      <div className="dispatch-card-copy">
        <div className="dispatch-meta">
          <span>{presentation.label}</span>
          <Importance value={item.importance} />
          <time dateTime={item.created_at}>Cycle {item.tick_number ?? item.tick_id}</time>
        </div>
        <h2>{item.headline}</h2>
        {item.body && <p>{item.body}</p>}
        <div className="dispatch-card-foot">
          <span>{formatDate(item.created_at)}</span>
          {destination && (
            <Link to={destination}>
              Inspect related asset <ArrowRight size={14} aria-hidden="true" />
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}

function Importance({ value }: { value: number }) {
  const safeValue = Math.max(1, Math.min(5, value));
  return (
    <span className="dispatch-importance" role="img" aria-label={`Importance ${safeValue} of 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <span key={index} className={index < safeValue ? "is-lit" : ""} aria-hidden="true" />
      ))}
    </span>
  );
}

function relatedDestination(item: NewsResponse): string | null {
  if (!item.related_entity_id) return null;
  if (item.related_entity_type === "GATE") return `/gates/${item.related_entity_id}`;
  if (item.related_entity_type === "GUILD") return `/guilds/${item.related_entity_id}`;
  return null;
}
