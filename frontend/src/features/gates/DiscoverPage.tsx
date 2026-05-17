import { useState } from "react";
import { useGateRankProfiles, useSubmitIntent } from "../../hooks/queries";
import { formatCurrency } from "../../utils/format";
import LoadingSpinner from "../../components/LoadingSpinner";
import ErrorAlert from "../../components/ErrorAlert";

export default function DiscoverPage() {
  const { data: profiles, isLoading, error } = useGateRankProfiles();
  const submitIntent = useSubmitIntent();
  const [selectedRank, setSelectedRank] = useState<string>("E");
  const [message, setMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  if (isLoading) return <LoadingSpinner />;
  if (error || !profiles) return <ErrorAlert message="Failed to load rank profiles" />;

  const selectedProfile =
    profiles.find((p) => p.rank === selectedRank) ?? profiles[0];

  const onDiscover = async () => {
    setMessage("");
    setErrorMsg("");
    try {
      await submitIntent.mutateAsync({
        intent_type: "DISCOVER_GATE",
        payload: { min_rank: selectedRank },
      });
      setMessage(`Discover intent queued for rank ${selectedRank}. It resolves on the next tick.`);
    } catch {
      setErrorMsg("Failed to submit discover intent.");
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="nm-page-title font-bold">Discover Gate</h1>
        <p className="nm-page-subtitle mt-1">
          Choose your minimum rank target. Higher rank floors cost more but can unlock stronger gates.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {profiles.map((profile) => {
          const active = profile.rank === selectedRank;
          return (
            <button
              key={profile.rank}
              onClick={() => setSelectedRank(profile.rank)}
              className={`text-left rounded-lg border p-4 transition-colors ${
                active
                  ? "border-brand-500 bg-brand-900/20"
                  : "border-gray-800 bg-gray-900 hover:border-gray-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">
                  {profile.rank === "S_PLUS" ? "S+" : profile.rank}
                </span>
                <span className="text-xs text-gray-500">Weight {profile.spawn_weight}</span>
              </div>
              <div className="mt-2 text-xs text-gray-400">
                Stability {profile.stability_init} | Vol {profile.volatility}
              </div>
              <div className="mt-1 text-xs text-gray-400">
                Yield {formatCurrency(profile.yield_min_micro)} - {formatCurrency(profile.yield_max_micro)}
              </div>
              <div className="mt-2 text-sm font-mono text-brand-300">
                Cost: {formatCurrency(profile.discovery_cost_micro)}
              </div>
            </button>
          );
        })}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
        <div className="text-sm text-gray-300">
          Selected minimum rank: <span className="font-semibold">{selectedRank}</span>
        </div>
        <div className="text-sm text-gray-400">
          Discovery cost: <span className="font-mono">{formatCurrency(selectedProfile.discovery_cost_micro)}</span>
        </div>
        <button
          onClick={onDiscover}
          disabled={submitIntent.isPending}
          className="bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium px-4 py-2 rounded disabled:opacity-50"
        >
          {submitIntent.isPending ? "Submitting..." : "Queue Discover Intent"}
        </button>
      </div>

      {errorMsg && (
        <div
          className="text-xs rounded px-3 py-2 border"
          style={{
            background: "linear-gradient(145deg, #ffe7e7, #ffdada)",
            borderColor: "#f3b5b5",
            color: "#af2f2f",
          }}
        >
          {errorMsg}
        </div>
      )}
      {message && (
        <div
          className="text-xs rounded px-3 py-2 border"
          style={{
            background: "linear-gradient(145deg, #e7f9ef, #daf5e5)",
            borderColor: "#bde8ce",
            color: "#1f7d49",
          }}
        >
          {message}
        </div>
      )}
    </div>
  );
}
