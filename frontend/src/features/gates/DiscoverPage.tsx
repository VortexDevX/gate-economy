import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Compass, Coins, Gem, Hourglass, Shield, Sparkles } from "lucide-react";
import { AxiosError } from "axios";
import type { ApiError } from "../../api/types";
import {
  GameButton,
  GamePanel,
  PlainTip,
  RankCrest,
  ScreenHeader,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import { useGateRankProfiles, useSimulationStatus, useSubmitIntent } from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency } from "../../utils/format";

export default function DiscoverPage() {
  const player = useAuthStore((state) => state.player);
  const { data: profiles, isLoading, error } = useGateRankProfiles();
  const { data: simulation } = useSimulationStatus();
  const submitIntent = useSubmitIntent();
  const [selectedRank, setSelectedRank] = useState("E");
  const [receipt, setReceipt] = useState<{ tone: "good" | "danger"; message: string } | null>(null);

  useEffect(() => {
    if (profiles?.length && !profiles.some((profile) => profile.rank === selectedRank)) {
      setSelectedRank(profiles[0].rank);
    }
  }, [profiles, selectedRank]);

  const selected = useMemo(
    () => profiles?.find((profile) => profile.rank === selectedRank) ?? profiles?.[0],
    [profiles, selectedRank],
  );
  const worldLive = Boolean(simulation?.is_running && !simulation?.is_paused);
  const canAfford = Boolean(selected && player && player.balance_micro >= selected.discovery_cost_micro);

  const launchExpedition = async () => {
    if (!selected || !worldLive || !canAfford) return;
    setReceipt(null);
    try {
      await submitIntent.mutateAsync({ intent_type: "DISCOVER_GATE", payload: { min_rank: selected.rank } });
      setReceipt({
        tone: "good",
        message: `Expedition command accepted. It will attempt a ${displayRank(selected.rank)}-rank-or-better discovery on the next world cycle.`,
      });
    } catch (requestError) {
      const detail = requestError instanceof AxiosError
        ? (requestError.response?.data as ApiError | undefined)?.detail
        : undefined;
      setReceipt({ tone: "danger", message: detail || "The expedition command could not be queued." });
    }
  };

  if (isLoading) return <LoadingSpinner className="py-24" />;
  if (error) return <ErrorAlert message="Expedition ranks could not be loaded." />;
  if (!profiles?.length || !selected) {
    return <ErrorAlert message="No gate rank profiles are configured. An operator must seed the system before expeditions can launch." />;
  }

  return (
    <div className="game-page expedition-page">
      <ScreenHeader
        eyebrow="Gate Atlas · Expedition desk"
        title="Launch an expedition"
        description="Pay a scouting cost, choose the minimum rank you are willing to accept, and let the next world cycle resolve the discovery."
      />

      <div className="expedition-layout">
        <section className="expedition-rank-section" aria-labelledby="rank-choice-title">
          <div className="expedition-section-heading">
            <span>Step 1</span>
            <div><h2 id="rank-choice-title">Choose your minimum gate rank</h2><p>Higher floors cost more and demand stronger risk tolerance.</p></div>
          </div>
          <div className="rank-choice-grid">
            {profiles.map((profile) => {
              const active = profile.rank === selected.rank;
              const affordable = (player?.balance_micro ?? 0) >= profile.discovery_cost_micro;
              return (
                <button
                  key={profile.rank}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setSelectedRank(profile.rank)}
                  className={`rank-choice-card ${active ? "is-selected" : ""} ${!affordable ? "is-unaffordable" : ""}`}
                >
                  <div className="rank-choice-top">
                    <RankCrest rank={profile.rank} size="lg" />
                    <div><span>Minimum rank</span><strong>{rankTitle(profile.rank)}</strong></div>
                    {!affordable && <span className="rank-lock">Too costly</span>}
                  </div>
                  <div className="rank-choice-price"><Coins size={15} /> ¤ {formatCurrency(profile.discovery_cost_micro)}</div>
                  <div className="rank-choice-traits">
                    <span><Shield size={14} /> {dangerLabel(profile.volatility)}</span>
                    <span><Gem size={14} /> {rarityLabel(profile.spawn_weight)}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <aside className="expedition-sidebar">
          <GamePanel className="expedition-contract" accent="gold">
            <div className="contract-heading">
              <span className="game-eyebrow">Step 2 · Confirm contract</span>
              <div className="contract-rank"><RankCrest rank={selected.rank} size="lg" /><div><span>Target</span><h2>{rankTitle(selected.rank)}</h2></div></div>
            </div>
            <dl className="contract-stats">
              <div><dt>Scouting cost</dt><dd>¤ {formatCurrency(selected.discovery_cost_micro)}</dd></div>
              <div><dt>Possible gate yield</dt><dd>¤ {formatCurrency(selected.yield_min_micro)}–{formatCurrency(selected.yield_max_micro)}</dd></div>
              <div><dt>Expected lifespan</dt><dd>{selected.lifespan_min}–{selected.lifespan_max} cycles</dd></div>
              <div><dt>Starts with</dt><dd>{selected.stability_init.toFixed(0)}% stability</dd></div>
              <div><dt>Your finder stake</dt><dd>10% of gate shares</dd></div>
            </dl>

            <PlainTip>
              This is a minimum rank, not a guaranteed exact result. A successful expedition can discover this rank or better.
            </PlainTip>

            {!worldLive && (
              <div className="contract-warning"><AlertTriangle size={17} /><span>The world is dormant. Expeditions cannot resolve until the simulation worker is running.</span></div>
            )}
            {worldLive && !canAfford && (
              <div className="contract-warning"><Coins size={17} /><span>You need ¤ {formatCurrency(selected.discovery_cost_micro - (player?.balance_micro ?? 0))} more coin for this expedition.</span></div>
            )}

            <GameButton
              onClick={launchExpedition}
              disabled={!worldLive || !canAfford || submitIntent.isPending}
              className="w-full"
            >
              {submitIntent.isPending ? <><Hourglass size={17} className="animate-spin" /> Sending command…</> : <><Compass size={18} /> Launch {displayRank(selected.rank)} expedition</>}
            </GameButton>
            <div className="contract-balance">Balance after launch: <strong>¤ {formatCurrency(Math.max(0, (player?.balance_micro ?? 0) - selected.discovery_cost_micro))}</strong></div>
          </GamePanel>

          <GamePanel className="expedition-explainer" accent="aether">
            <Sparkles size={21} aria-hidden="true" />
            <div><h3>What happens next?</h3><p>Your command enters the Action Queue. On the next cycle, the game charges the cost, creates the gate, and grants your finder shares—or explains why it failed.</p></div>
          </GamePanel>
        </aside>
      </div>

      {receipt && <div className={`game-receipt game-receipt-${receipt.tone}`} role="status">{receipt.message}</div>}
    </div>
  );
}

function displayRank(rank: string) { return rank === "S_PLUS" ? "S+" : rank; }
function rankTitle(rank: string) {
  const labels: Record<string, string> = { E: "Fledgling Rift", D: "Wayward Gate", C: "Veteran Breach", B: "Warlord Gate", A: "Sovereign Rift", S: "Calamity Gate", S_PLUS: "Abyssal Crown" };
  return labels[rank] ?? `${displayRank(rank)}-rank gate`;
}
function dangerLabel(volatility: number) {
  if (volatility <= 0.08) return "Low turbulence";
  if (volatility <= 0.15) return "Rising danger";
  if (volatility <= 0.22) return "High danger";
  return "Extreme danger";
}
function rarityLabel(weight: number) {
  if (weight >= 25) return "Common";
  if (weight >= 10) return "Uncommon";
  if (weight >= 5) return "Rare";
  return "Mythic";
}
