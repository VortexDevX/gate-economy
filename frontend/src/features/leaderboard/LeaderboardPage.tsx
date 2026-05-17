import { useEffect, useMemo, useState } from "react";
import {
  useCurrentSeason,
  useLeaderboard,
  useMyRank,
  useSeasonResults,
  useSeasons,
} from "../../hooks/queries";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";
import Pagination from "../../components/Pagination";
import { formatCurrency, shortId } from "../../utils/format";

const PAGE_SIZE = 20;

export default function LeaderboardPage() {
  const [page, setPage] = useState(1);
  const { data: board, isLoading: boardLoading, error: boardError } = useLeaderboard({
    page,
    page_size: PAGE_SIZE,
  });
  const { data: myRank } = useMyRank();

  const { data: currentSeason } = useCurrentSeason();
  const { data: seasons } = useSeasons({ page: 1, page_size: 10 });
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | null>(null);

  useEffect(() => {
    if (selectedSeasonId == null && currentSeason?.id) {
      setSelectedSeasonId(currentSeason.id);
    }
  }, [selectedSeasonId, currentSeason]);

  const { data: results, isLoading: resultsLoading } = useSeasonResults(
    selectedSeasonId,
    { page: 1, page_size: 20 },
  );

  const totalPages = board ? Math.ceil(board.total / PAGE_SIZE) : 0;
  const myRowHighlighted = useMemo(
    () => !!(myRank && board?.entries.some((e) => e.player_id === myRank.player_id)),
    [myRank, board],
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div><h1 className="nm-page-title font-bold">Leaderboard and Seasons</h1><p className="nm-page-subtitle mt-1">Monitor season performance, your rank trajectory, and final snapshots.</p></div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card label="Current Season">
          {currentSeason
            ? `#${currentSeason.season_number} (${currentSeason.status})`
            : "No live season"}
        </Card>
        <Card label="My Rank">
          {myRank?.rank != null ? `#${myRank.rank}` : "Unranked"}
        </Card>
        <Card label="My Net Worth">
          {myRank ? formatCurrency(myRank.net_worth_micro) : "0.00"}
        </Card>
      </div>

      {boardLoading && <LoadingSpinner />}
      {boardError && <ErrorAlert message="Failed to load leaderboard" />}
      {board && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Current Rankings</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="py-2 pr-4">Rank</th>
                  <th className="py-2 pr-4">Player</th>
                  <th className="py-2 pr-4">Score</th>
                  <th className="py-2 pr-4">Net Worth</th>
                  <th className="py-2 pr-4">Balance</th>
                  <th className="py-2">Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {board.entries.map((entry) => {
                  const mine = myRank?.player_id === entry.player_id;
                  return (
                    <tr
                      key={entry.player_id}
                      className={`border-b border-gray-800/50 ${
                        mine ? "bg-brand-900/20" : "hover:bg-gray-900/50"
                      }`}
                    >
                      <td className="py-2 pr-4 font-semibold">#{entry.rank}</td>
                      <td className="py-2 pr-4">
                        <div className="text-gray-200">{entry.username}</div>
                        <div className="text-xs font-mono text-gray-500">
                          {shortId(entry.player_id)}
                        </div>
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {formatCurrency(entry.score_micro)}
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {formatCurrency(entry.net_worth_micro)}
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {formatCurrency(entry.balance_micro)}
                      </td>
                      <td className="py-2 font-mono">
                        {formatCurrency(entry.portfolio_micro)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
          {!myRowHighlighted && myRank?.rank != null && (
            <div className="text-xs text-gray-500 mt-3">
              Your rank exists but is outside this page window.
            </div>
          )}
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
        <h2 className="text-sm uppercase tracking-wider text-gray-400">Season Results</h2>
        <div className="flex flex-wrap gap-2">
          {seasons?.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedSeasonId(s.id)}
              className={`text-xs px-2.5 py-1 rounded border ${
                selectedSeasonId === s.id
                  ? "border-brand-500 text-brand-300 bg-brand-900/20"
                  : "border-gray-700 text-gray-300 bg-gray-950 hover:border-gray-600"
              }`}
            >
              S{s.season_number} {s.status === "COMPLETED" ? "(Done)" : "(Live)"}
            </button>
          ))}
        </div>

        {resultsLoading && <LoadingSpinner className="py-6" />}
        {!resultsLoading && selectedSeasonId != null && results && results.length === 0 && (
          <div className="text-sm text-gray-500">No result rows available for this season yet.</div>
        )}
        {!resultsLoading && results && results.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="py-2 pr-4">Final Rank</th>
                  <th className="py-2 pr-4">Username</th>
                  <th className="py-2 pr-4">Final Score</th>
                  <th className="py-2">Final Net Worth</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.player_id} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4">#{r.final_rank}</td>
                    <td className="py-2 pr-4">{r.username}</td>
                    <td className="py-2 pr-4 font-mono">
                      {formatCurrency(r.final_score_micro)}
                    </td>
                    <td className="py-2 font-mono">
                      {formatCurrency(r.final_net_worth_micro)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      <div className="text-xs uppercase tracking-wider text-gray-400 mb-1">{label}</div>
      <div className="text-base font-semibold">{children}</div>
    </div>
  );
}

