import { useState } from "react";
import {
  Coins,
  Crown,
  Landmark,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  UsersRound,
} from "lucide-react";
import type { GuildResponse } from "../../api/types";
import {
  GameAction,
  GameButton,
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import Pagination from "../../components/Pagination";
import { useGuilds } from "../../hooks/queries";
import { formatCurrency, formatPercent } from "../../utils/format";

const STATUSES = ["", "ACTIVE", "INSOLVENT", "DISSOLVED"] as const;
const PAGE_SIZE = 12;

export default function GuildsListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const guildsQuery = useGuilds({
    status: statusFilter || undefined,
    offset,
    limit: PAGE_SIZE,
  });

  const guilds = guildsQuery.data?.guilds ?? [];
  const totalPages = guildsQuery.data
    ? Math.ceil(guildsQuery.data.total / PAGE_SIZE)
    : 0;
  const visibleTreasury = guilds.reduce(
    (sum, guild) => sum + guild.treasury_micro,
    0,
  );
  const operating = guilds.filter((guild) => guild.status === "ACTIVE").length;
  const endangered = guilds.filter((guild) => guild.status === "INSOLVENT").length;

  return (
    <div className="game-page guild-hall-page">
      <ScreenHeader
        eyebrow="Guild Hall · Shared treasuries"
        title="Build Power Beyond One Hunter"
        description="Guilds pool coin, hold gate shares, issue their own shares, and can reward owners with dividends. They are a later-game strategy—not the first step for a new account."
        action={<GameAction to="/guilds/create"><Sparkles size={17} aria-hidden="true" /> Found a guild</GameAction>}
      />

      <PlainTip>
        A guild needs enough treasury coin to survive upkeep. Inspect its treasury and policy before buying guild shares.
      </PlainTip>

      <section className="guild-hall-stats" aria-label="Guild hall summary">
        <StatRune
          label="Guilds found"
          value={String(guildsQuery.data?.total ?? 0)}
          note="All guilds matching the current world"
          tone="violet"
          icon={<Shield size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Operating here"
          value={String(operating)}
          note="Active guilds visible on this page"
          tone={operating ? "good" : "muted"}
          icon={<UsersRound size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Visible treasury"
          value={`¤ ${formatCurrency(visibleTreasury)}`}
          note="Combined coin held by guilds on this page"
          tone="gold"
          icon={<Coins size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Treasuries in danger"
          value={String(endangered)}
          note="Guilds currently unable to meet obligations"
          tone={endangered ? "danger" : "good"}
          icon={<ShieldAlert size={18} aria-hidden="true" />}
        />
      </section>

      <GamePanel className="guild-hall-filter-panel" accent="muted">
        <PanelHeading
          title="Choose a hall"
          detail="Compare operating guilds, endangered treasuries, and closed records."
          action={statusFilter && (
            <GameButton
              tone="ghost"
              onClick={() => {
                setStatusFilter("");
                setPage(1);
              }}
            >
              Clear filter
            </GameButton>
          )}
        />
        <div className="guild-hall-filters" role="group" aria-label="Filter guilds by condition">
          {STATUSES.map((status) => (
            <button
              key={status || "ALL"}
              type="button"
              className={`guild-hall-filter guild-hall-filter-${status ? status.toLowerCase() : "all"} ${statusFilter === status ? "is-active" : ""}`}
              onClick={() => {
                setStatusFilter(status);
                setPage(1);
              }}
              aria-pressed={statusFilter === status}
            >
              {plainStatus(status)}
            </button>
          ))}
        </div>
      </GamePanel>

      {guildsQuery.isLoading && <LoadingSpinner />}
      {guildsQuery.error && (
        <ErrorAlert message="The Guild Hall register could not be opened. No guild treasury or membership was changed." />
      )}
      {!guildsQuery.isLoading && !guildsQuery.error && guilds.length === 0 && (
        <GamePanel className="guild-hall-empty-panel" accent="muted">
          <GameEmpty
            title={statusFilter ? "No guild matches this condition" : "No banners hang in the hall yet"}
            message={statusFilter
              ? "Clear the filter to inspect every guild in the realm."
              : "Founding a guild is expensive. Grow through gate ownership first, then return when you can support a treasury."}
            action={statusFilter
              ? undefined
              : { to: "/guide", label: "Learn when to found a guild" }}
          />
        </GamePanel>
      )}

      {guilds.length > 0 && (
        <section className="guild-hall-grid" aria-label="Guilds">
          {guilds.map((guild) => (
            <GuildCard key={guild.id} guild={guild} />
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

function GuildCard({ guild }: { guild: GuildResponse }) {
  const status = guild.status.toLowerCase();
  const treasuryCycles = guild.maintenance_cost_micro > 0
    ? guild.treasury_micro / guild.maintenance_cost_micro
    : null;
  return (
    <GamePanel className={`guild-hall-card guild-hall-card-${status}`} accent={guildTone(guild.status)}>
      <div className="guild-hall-card-head">
        <div className="guild-hall-crest" aria-hidden="true">
          <Shield size={32} />
          <span>{guildInitials(guild.name)}</span>
        </div>
        <div className="guild-hall-card-title">
          <span className={`guild-hall-status guild-hall-status-${status}`}>
            {plainStatus(guild.status)}
          </span>
          <h2>{guild.name}</h2>
          <p>Founded in cycle {guild.created_at_tick}</p>
        </div>
      </div>

      <div className="guild-hall-treasury">
        <span><Landmark size={17} aria-hidden="true" /> Treasury</span>
        <strong>¤ {formatCurrency(guild.treasury_micro)}</strong>
        <small>
          {treasuryCycles == null
            ? "No recurring upkeep is recorded"
            : `${treasuryCycles.toFixed(1)} cycles of current upkeep held`}
        </small>
      </div>

      <dl className="guild-hall-economy">
        <div>
          <dt><Crown size={15} aria-hidden="true" /> Total shares</dt>
          <dd>{guild.total_shares}</dd>
        </div>
        <div>
          <dt><Scale size={15} aria-hidden="true" /> Publicly tradeable</dt>
          <dd>{formatPercent(guild.public_float_pct)}</dd>
        </div>
        <div>
          <dt><Coins size={15} aria-hidden="true" /> Upkeep / cycle</dt>
          <dd>¤ {formatCurrency(guild.maintenance_cost_micro)}</dd>
        </div>
        <div>
          <dt><UsersRound size={15} aria-hidden="true" /> Reward policy</dt>
          <dd>{plainDividendPolicy(guild)}</dd>
        </div>
      </dl>

      <GameAction to={`/guilds/${guild.id}`} tone="secondary" className="guild-hall-open">
        Enter guild hall
      </GameAction>
    </GamePanel>
  );
}

function plainStatus(status: string): string {
  const labels: Record<string, string> = {
    "": "Every guild",
    ACTIVE: "Operating",
    INSOLVENT: "Treasury in danger",
    DISSOLVED: "Closed",
  };
  return labels[status] ?? sentenceCase(status);
}

function plainDividendPolicy(guild: GuildResponse): string {
  if (guild.dividend_policy === "AUTO") {
    return guild.auto_dividend_pct != null
      ? `Automatic · ${formatPercent(guild.auto_dividend_pct)}`
      : "Automatic rewards";
  }
  if (guild.dividend_policy === "MANUAL") return "Leader decides";
  return sentenceCase(guild.dividend_policy);
}

function guildInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "G";
}

function guildTone(status: string): "good" | "warn" | "danger" | "violet" {
  if (status === "ACTIVE") return "good";
  if (status === "INSOLVENT") return "warn";
  if (status === "DISSOLVED") return "danger";
  return "violet";
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
