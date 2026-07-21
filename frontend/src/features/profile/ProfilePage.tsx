import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowDownLeft,
  ArrowUpRight,
  BookOpenText,
  Crown,
  Landmark,
  Shield,
  TrendingUp,
  UserRound,
  WalletCards,
} from "lucide-react";
import type { LedgerEntryResponse } from "../../api/types";
import {
  GameAction,
  GameEmpty,
  GamePanel,
  PanelHeading,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import Pagination from "../../components/Pagination";
import { useMyLedger, useMyPortfolio } from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency, formatDate } from "../../utils/format";

const PAGE_SIZE = 20;

export default function ProfilePage() {
  const player = useAuthStore((state) => state.player);
  const [page, setPage] = useState(1);
  const ledgerQuery = useMyLedger({ page, size: PAGE_SIZE });
  const portfolioQuery = useMyPortfolio();

  if (!player) return null;

  const portfolio = portfolioQuery.data;
  const ledger = ledgerQuery.data;
  const totalPages = ledger ? Math.ceil(ledger.total / PAGE_SIZE) : 0;
  const positions = [
    ...(portfolio?.gate_positions ?? []).map((position) => ({
      kind: "gate" as const,
      id: position.gate_id,
      name: position.display_name,
      value: position.market_value_micro,
      detail: `${position.quantity} shares · ${plainRisk(position.risk_band)}`,
      tone: position.risk_band === "CRITICAL" ? "danger" : position.risk_band === "WATCH" ? "warn" : "good",
      gate: position,
    })),
    ...(portfolio?.guild_positions ?? []).map((position) => ({
      kind: "guild" as const,
      id: position.guild_id,
      name: position.name,
      value: position.market_value_micro,
      detail: `${position.quantity} shares · ${plainGuildStatus(position.status)}`,
      tone: position.status === "ACTIVE" ? "violet" : "warn",
      guild: position,
    })),
  ].sort((a, b) => b.value - a.value);

  return (
    <div className="game-page vault-page">
      <ScreenHeader
        eyebrow="Hunter chronicle · Wealth and history"
        title={`${player.username}'s Chronicle`}
        description="See what you own, what it is worth, what it may earn next cycle, and every movement of coin recorded by the exchange."
        action={<GameAction to="/gates">Grow your holdings</GameAction>}
      />

      {portfolioQuery.error && (
        <ErrorAlert message="Your live holdings could not be valued. Your permanent coin history remains available below." />
      )}

      <section className="vault-stats" aria-label="Wealth summary">
        <StatRune
          label="Coin ready"
          value={`¤ ${formatCurrency(portfolio?.cash_balance_micro ?? player.balance_micro)}`}
          note={portfolio?.reserved_cash_micro
            ? `¤ ${formatCurrency(portfolio.reserved_cash_micro)} is committed to open orders`
            : "Available for expeditions and trades"}
          tone="gold"
          icon={<WalletCards size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Total worth"
          value={`¤ ${formatCurrency(portfolio?.net_worth_micro ?? player.balance_micro)}`}
          note="Ready coin, locked coin, and marked holdings"
          tone="aether"
          icon={<Crown size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Income next cycle"
          value={`+¤ ${formatCurrency(portfolio?.projected_yield_per_tick_micro ?? 0)}`}
          note="Expected from active gate shares"
          tone="good"
          icon={<TrendingUp size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Owned positions"
          value={String(positions.length)}
          note={`${portfolio?.gate_positions.length ?? 0} gates · ${portfolio?.guild_positions.length ?? 0} guilds`}
          tone={positions.length ? "violet" : "muted"}
          icon={<Shield size={18} aria-hidden="true" />}
        />
      </section>

      <section className="vault-overview-grid">
        <GamePanel className="vault-identity" accent="violet">
          <div className="vault-portrait" aria-hidden="true">
            <UserRound size={42} />
            <span>{initials(player.username)}</span>
          </div>
          <div className="vault-identity-copy">
            <span className="vault-role">{player.role === "ADMIN" ? "Exchange Keeper" : "Licensed Gate Hunter"}</span>
            <h2>{player.username}</h2>
            <p>
              Chronicle opened {new Date(player.created_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
          <div className="vault-seal" title="Identity verified by the exchange">
            <BookOpenText size={22} aria-hidden="true" />
            <span>Verified</span>
          </div>
        </GamePanel>

        <GamePanel className="vault-holdings" accent="gold">
          <PanelHeading
            title="Holdings at a glance"
            detail="Largest positions first, valued at the latest market mark."
            action={<span className="vault-count">Cycle {portfolio?.as_of_tick ?? "—"}</span>}
          />
          {portfolioQuery.isLoading && <LoadingSpinner />}
          {!portfolioQuery.isLoading && !portfolioQuery.error && positions.length === 0 && (
            <GameEmpty
              title="Your vault holds only coin"
              message="Scout a gate to earn a finder stake, or buy shares from an existing gate."
              action={{ to: "/discover", label: "Scout your first gate" }}
            />
          )}
          {positions.length > 0 && (
            <div className="vault-position-list">
              {positions.slice(0, 6).map((position) => (
                <Link
                  key={`${position.kind}-${position.id}`}
                  to={position.kind === "gate" ? `/gates/${position.id}` : `/guilds/${position.id}`}
                  className={`vault-position vault-position-${position.tone}`}
                >
                  <span className="vault-position-icon">
                    {position.kind === "gate"
                      ? <Landmark size={18} aria-hidden="true" />
                      : <Shield size={18} aria-hidden="true" />}
                  </span>
                  <div>
                    <h3>{position.name}</h3>
                    <p>{position.detail}</p>
                  </div>
                  <strong>¤ {formatCurrency(position.value)}</strong>
                </Link>
              ))}
            </div>
          )}
        </GamePanel>
      </section>

      <GamePanel className="vault-ledger" accent="aether">
        <PanelHeading
          title="Coin Chronicle"
          detail="A permanent trail of income, purchases, fees, and transfers."
          action={ledger && <span className="vault-count">{ledger.total} entries</span>}
        />
        {ledgerQuery.isLoading && <LoadingSpinner />}
        {ledgerQuery.error && (
          <ErrorAlert message="Your coin chronicle could not be opened. No balance or history was changed." />
        )}
        {!ledgerQuery.isLoading && !ledgerQuery.error && ledger?.items.length === 0 && (
          <GameEmpty
            title="No coin has moved yet"
            message="Your first expedition, trade, or gate payout will create the first line in this chronicle."
            action={{ to: "/discover", label: "Begin an expedition" }}
          />
        )}
        {ledger && ledger.items.length > 0 && (
          <ol className="vault-ledger-list" aria-label="Coin history">
            {ledger.items.map((entry) => (
              <LedgerRow key={entry.id} entry={entry} playerId={player.id} />
            ))}
          </ol>
        )}
        {totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        )}
      </GamePanel>
    </div>
  );
}

function LedgerRow({
  entry,
  playerId,
}: {
  entry: LedgerEntryResponse;
  playerId: string;
}) {
  const incoming = entry.credit_id === playerId;
  const presentation = ledgerPresentation(entry.entry_type, incoming);
  return (
    <li className={`vault-ledger-row ${incoming ? "vault-ledger-in" : "vault-ledger-out"}`}>
      <span className="vault-ledger-icon">
        {incoming
          ? <ArrowDownLeft size={19} aria-hidden="true" />
          : <ArrowUpRight size={19} aria-hidden="true" />}
      </span>
      <div className="vault-ledger-copy">
        <div>
          <h3>{presentation.title}</h3>
          <span>{entry.tick_id != null ? `Settlement #${entry.tick_id}` : "Outside cycle settlement"}</span>
        </div>
        <p>{entry.memo || presentation.copy}</p>
      </div>
      <div className="vault-ledger-amount">
        <strong>{incoming ? "+" : "−"}¤ {formatCurrency(entry.amount_micro)}</strong>
        <span>{formatDate(entry.created_at)}</span>
      </div>
    </li>
  );
}

function ledgerPresentation(entryType: string, incoming: boolean): { title: string; copy: string } {
  const labels: Record<string, { title: string; copy: string }> = {
    INITIAL_SEED: { title: "Starting purse", copy: "Coin issued when this chronicle was opened." },
    GATE_YIELD: { title: "Gate income", copy: "An active gate paid its owners for a completed cycle." },
    DISCOVERY_FEE: { title: "Expedition funded", copy: "Coin spent to send hunters searching for a new gate." },
    ORDER_ESCROW: { title: "Coin committed", copy: "Coin reserved behind an open buy order." },
    ESCROW_RELEASE: { title: "Coin released", copy: "Unused order coin returned to your ready balance." },
    TRADE: { title: incoming ? "Share sale" : "Share purchase", copy: incoming ? "Coin received from a matched sell order." : "Coin paid for matched shares." },
    TRADE_FEE: { title: "Exchange fee", copy: "A fee charged when an order matched." },
    GUILD_FOUNDING: { title: "Guild founded", copy: "Coin committed to launch a new guild treasury." },
    DIVIDEND: { title: "Guild dividend", copy: "A guild distributed coin to its shareholders." },
  };
  return labels[entryType] ?? {
    title: sentenceCase(entryType),
    copy: incoming ? "Coin entered your balance." : "Coin left your balance.",
  };
}

function initials(username: string): string {
  return username
    .split(/[\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "H";
}

function plainRisk(risk: string): string {
  const labels: Record<string, string> = {
    STABLE: "Safe",
    WATCH: "Needs watching",
    CRITICAL: "Near collapse",
    OFFERING: "Preparing to open",
    COLLAPSED: "Lost",
  };
  return labels[risk] ?? sentenceCase(risk);
}

function plainGuildStatus(status: string): string {
  const labels: Record<string, string> = {
    ACTIVE: "Operating",
    INSOLVENT: "Treasury in danger",
    DISSOLVED: "Closed",
  };
  return labels[status] ?? sentenceCase(status);
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
