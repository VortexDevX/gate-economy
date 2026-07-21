import { useEffect, useMemo, useState } from "react";
import {
  Award,
  Crown,
  Gem,
  Medal,
  Shield,
  Swords,
  Trophy,
  WalletCards,
} from "lucide-react";
import type {
  LeaderboardEntryResponse,
  SeasonResultResponse,
} from "../../api/types";
import {
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
import {
  useCurrentSeason,
  useLeaderboard,
  useMyRank,
  useSeasonResults,
  useSeasons,
} from "../../hooks/queries";
import { formatCurrency } from "../../utils/format";

const PAGE_SIZE = 20;

export default function LeaderboardPage() {
  const [page, setPage] = useState(1);
  const boardQuery = useLeaderboard({ page, page_size: PAGE_SIZE });
  const myRankQuery = useMyRank();
  const currentSeasonQuery = useCurrentSeason();
  const seasonsQuery = useSeasons({ page: 1, page_size: 10 });
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | null>(null);

  useEffect(() => {
    if (selectedSeasonId == null) {
      const firstAvailableSeason = currentSeasonQuery.data?.id ?? seasonsQuery.data?.[0]?.id;
      if (firstAvailableSeason != null) {
        setSelectedSeasonId(firstAvailableSeason);
      }
    }
  }, [selectedSeasonId, currentSeasonQuery.data, seasonsQuery.data]);

  const resultsQuery = useSeasonResults(selectedSeasonId, {
    page: 1,
    page_size: 20,
  });
  const board = boardQuery.data;
  const myRank = myRankQuery.data;
  const currentSeason = currentSeasonQuery.data;
  const seasons = seasonsQuery.data ?? [];
  const results = resultsQuery.data ?? [];
  const totalPages = board ? Math.ceil(board.total / PAGE_SIZE) : 0;
  const myRowVisible = useMemo(
    () => Boolean(myRank && board?.entries.some((entry) => entry.player_id === myRank.player_id)),
    [myRank, board],
  );
  const seasonLength = currentSeason?.end_tick != null
    ? Math.max(0, currentSeason.end_tick - currentSeason.start_tick)
    : null;

  return (
    <div className="game-page season-page">
      <ScreenHeader
        eyebrow="Season Crown · Realm standings"
        title="Climb Above the Other Hunters"
        description="Rank is driven by economic strength. Grow total worth, protect it through gate collapses, and finish the season with more value than your rivals."
      />

      <PlainTip>
        Ready coin alone does not decide rank. Your marked gate and guild holdings also count toward total worth and season score.
      </PlainTip>

      <section className="season-stats" aria-label="Your season standing">
        <StatRune
          label="Current season"
          value={currentSeason ? `Season ${currentSeason.season_number}` : "No live season"}
          note={currentSeason
            ? `${plainSeasonStatus(currentSeason.status)}${seasonLength != null ? ` · ${seasonLength} scheduled cycles` : ""}`
            : "The next contest has not begun"}
          tone="violet"
          icon={<Crown size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Your place"
          value={myRank?.rank != null ? `#${myRank.rank}` : "Unranked"}
          note={myRank?.rank != null ? `Out of ${board?.total ?? "—"} ranked hunters` : "Enter the economy to earn a place"}
          tone={myRank?.rank != null ? "gold" : "muted"}
          icon={<Trophy size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Your total worth"
          value={`¤ ${formatCurrency(myRank?.net_worth_micro ?? 0)}`}
          note="Coin plus marked holdings"
          tone="aether"
          icon={<WalletCards size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Season score"
          value={`¤ ${formatCurrency(myRank?.score_micro ?? 0)}`}
          note={myRank ? `Last counted in cycle ${myRank.updated_at_tick}` : "No score recorded yet"}
          tone="good"
          icon={<Gem size={18} aria-hidden="true" />}
        />
      </section>

      {boardQuery.isLoading && <LoadingSpinner />}
      {boardQuery.error && (
        <ErrorAlert message="The current standings could not be loaded. Season scores remain safely recorded." />
      )}
      {!boardQuery.isLoading && !boardQuery.error && board && board.entries.length === 0 && (
        <GamePanel className="season-empty-panel" accent="muted">
          <GameEmpty
            title="No hunter has claimed a rank"
            message="The standings appear after players begin building measurable wealth in the world."
            action={{ to: "/discover", label: "Begin your first expedition" }}
          />
        </GamePanel>
      )}

      {board && board.entries.length > 0 && (
        <GamePanel className="season-rankings" accent="gold">
          <PanelHeading
            title="Live standings"
            detail="Current economic power, recalculated as the world advances."
            action={<span className="season-count">{board.total} ranked</span>}
          />
          <div className="season-ranking-list" role="list" aria-label="Current season rankings">
            {board.entries.map((entry) => (
              <RankingRow
                key={entry.player_id}
                entry={entry}
                mine={myRank?.player_id === entry.player_id}
              />
            ))}
          </div>
          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
          {!myRowVisible && myRank?.rank != null && (
            <div className="season-my-rank" role="status">
              <Shield size={18} aria-hidden="true" />
              <div>
                <span>Your position is outside this page</span>
                <strong>Rank #{myRank.rank} · ¤ {formatCurrency(myRank.net_worth_micro)} total worth</strong>
              </div>
            </div>
          )}
        </GamePanel>
      )}

      <GamePanel className="season-archive" accent="violet">
        <PanelHeading
          title="Season archive"
          detail="Choose a season to inspect its final champions and preserved scores."
        />
        {seasonsQuery.isLoading && <LoadingSpinner className="season-archive-loading" />}
        {seasonsQuery.error && (
          <ErrorAlert message="The season archive could not be opened." />
        )}
        {seasons.length === 0 && !seasonsQuery.isLoading && !seasonsQuery.error && (
          <GameEmpty
            title="No season has been written into history"
            message="When the first season begins, its live state and eventual winners will appear here."
          />
        )}
        {seasons.length > 0 && (
          <div className="season-selector" role="group" aria-label="Choose a season">
            {seasons.map((season) => (
              <button
                key={season.id}
                type="button"
                onClick={() => setSelectedSeasonId(season.id)}
                className={`season-selector-button ${selectedSeasonId === season.id ? "is-active" : ""}`}
                aria-pressed={selectedSeasonId === season.id}
              >
                <Crown size={16} aria-hidden="true" />
                <span>Season {season.season_number}</span>
                <small>{plainSeasonStatus(season.status)}</small>
              </button>
            ))}
          </div>
        )}

        {resultsQuery.isLoading && <LoadingSpinner className="season-results-loading" />}
        {resultsQuery.error && (
          <ErrorAlert message="The final standings for this season could not be read." />
        )}
        {!resultsQuery.isLoading && !resultsQuery.error && selectedSeasonId != null && results.length === 0 && (
          <div className="season-results-pending">
            <Swords size={22} aria-hidden="true" />
            <div>
              <h3>The contest is not settled</h3>
              <p>Final champions are recorded only after a season closes.</p>
            </div>
          </div>
        )}
        {results.length > 0 && (
          <div className="season-results" role="list" aria-label="Final season standings">
            {results.map((result) => (
              <SeasonResult key={result.player_id} result={result} />
            ))}
          </div>
        )}
      </GamePanel>
    </div>
  );
}

function RankingRow({
  entry,
  mine,
}: {
  entry: LeaderboardEntryResponse;
  mine: boolean;
}) {
  return (
    <article
      className={`season-ranking-row season-place-${Math.min(entry.rank, 4)} ${mine ? "is-mine" : ""}`}
      role="listitem"
      aria-label={`${entry.username}, rank ${entry.rank}${mine ? ", your position" : ""}`}
    >
      <PlaceMark rank={entry.rank} />
      <div className="season-player">
        <div>
          <h3>{entry.username}</h3>
          {mine && <span>Your chronicle</span>}
        </div>
        <strong>¤ {formatCurrency(entry.score_micro)} score</strong>
      </div>
      <dl className="season-economy">
        <div><dt>Total worth</dt><dd>¤ {formatCurrency(entry.net_worth_micro)}</dd></div>
        <div><dt>Ready coin</dt><dd>¤ {formatCurrency(entry.balance_micro)}</dd></div>
        <div><dt>Holdings</dt><dd>¤ {formatCurrency(entry.portfolio_micro)}</dd></div>
      </dl>
    </article>
  );
}

function SeasonResult({ result }: { result: SeasonResultResponse }) {
  return (
    <article className={`season-result season-place-${Math.min(result.final_rank, 4)}`} role="listitem">
      <PlaceMark rank={result.final_rank} />
      <div>
        <h3>{result.username}</h3>
        <span>Final score ¤ {formatCurrency(result.final_score_micro)}</span>
      </div>
      <strong>¤ {formatCurrency(result.final_net_worth_micro)} worth</strong>
    </article>
  );
}

function PlaceMark({ rank }: { rank: number }) {
  const Icon = rank === 1 ? Crown : rank <= 3 ? Medal : Award;
  return (
    <span className={`season-place-mark season-place-mark-${Math.min(rank, 4)}`}>
      <Icon size={rank <= 3 ? 22 : 18} aria-hidden="true" />
      <strong>#{rank}</strong>
    </span>
  );
}

function plainSeasonStatus(status: string): string {
  const labels: Record<string, string> = {
    ACTIVE: "Live now",
    COMPLETED: "Finished",
    PENDING: "Preparing",
    CANCELLED: "Closed without a winner",
  };
  return labels[status] ?? sentenceCase(status);
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
