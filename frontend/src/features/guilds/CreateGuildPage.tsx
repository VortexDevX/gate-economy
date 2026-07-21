import { useId, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Coins,
  Crown,
  Landmark,
  Percent,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  GameButton,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
import { useSubmitIntent } from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency } from "../../utils/format";

const GUILD_CREATION_COST_MICRO = 50_000_000;

export default function CreateGuildPage() {
  const navigate = useNavigate();
  const submitIntent = useSubmitIntent();
  const player = useAuthStore((state) => state.player);
  const nameId = useId();
  const floatId = useId();
  const policyId = useId();
  const autoDividendId = useId();

  const [name, setName] = useState("");
  const [publicFloatPct, setPublicFloatPct] = useState("0.20");
  const [dividendPolicy, setDividendPolicy] = useState("MANUAL");
  const [autoDividendPct, setAutoDividendPct] = useState("0.10");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const floatVal = Number(publicFloatPct);
  const autoVal = Number(autoDividendPct);
  const floatDisplay = Number.isFinite(floatVal) ? floatVal * 100 : 0;
  const founderDisplay = Number.isFinite(floatVal) ? (1 - floatVal) * 100 : 0;
  const hasCreationFunds = (player?.balance_micro ?? 0) >= GUILD_CREATION_COST_MICRO;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!name.trim()) {
      setErrorMsg("Give your guild a name before founding it.");
      return;
    }
    if (Number.isNaN(floatVal) || floatVal < 0 || floatVal > 0.49) {
      setErrorMsg("Public float must be between 0.00 and 0.49 (0% to 49%).");
      return;
    }
    if (dividendPolicy === "AUTO_FIXED_PCT") {
      if (Number.isNaN(autoVal) || autoVal <= 0 || autoVal > 1) {
        setErrorMsg("Automatic dividends must be greater than 0 and no more than 1.00 (100%).");
        return;
      }
    }

    const payload: Record<string, unknown> = {
      name: name.trim(),
      public_float_pct: floatVal,
      dividend_policy: dividendPolicy,
    };
    if (dividendPolicy === "AUTO_FIXED_PCT") {
      payload.auto_dividend_pct = autoVal;
    }

    try {
      await submitIntent.mutateAsync({
        intent_type: "CREATE_GUILD",
        payload,
      });
      setSuccessMsg(
        "Founding order queued. No coin has moved yet; the next world cycle will validate the cost and create the guild.",
      );
      setTimeout(() => navigate("/guilds"), 1200);
    } catch {
      setErrorMsg("The founding order could not be queued. Your coin was not changed.");
    }
  };

  return (
    <div className="game-page guild-forge-page grid gap-[18px]">
      <ScreenHeader
        eyebrow="Guild forge · Late-game command"
        title="Raise a Guild Banner"
        description="Spend 50 coin to found a shared treasury, choose how many shares the public may trade, and decide how future rewards leave the vault."
        action={(
          <Link to="/guilds" className="game-action game-action-ghost guild-forge-back">
            <ArrowLeft size={17} aria-hidden="true" />
            <span>Return to Guild Hall</span>
          </Link>
        )}
      />

      <section className="guild-forge-stats grid grid-cols-1 gap-2 sm:grid-cols-3" aria-label="Guild founding requirements">
        <StatRune
          label="Founding cost"
          value={`¤ ${formatCurrency(GUILD_CREATION_COST_MICRO)}`}
          note="Charged only if the next cycle accepts the order"
          tone="gold"
          icon={<Coins size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Your available coin"
          value={`¤ ${formatCurrency(player?.balance_micro ?? 0)}`}
          note={hasCreationFunds ? "You currently meet the founding cost" : "Build your gate portfolio before founding"}
          tone={hasCreationFunds ? "good" : "warn"}
          icon={hasCreationFunds ? <ShieldCheck size={18} aria-hidden="true" /> : <AlertTriangle size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Resolution"
          value="Next cycle"
          note="This screen queues a command; it is not instant"
          tone="aether"
          icon={<Clock3 size={18} aria-hidden="true" />}
        />
      </section>

      <PlainTip>
        Founding is a commitment, not a beginner quest. The guild pays upkeep each cycle, so keep personal coin in reserve after the 50-coin cost.
      </PlainTip>

      <div className="guild-forge-layout grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(300px,.75fr)]">
        <GamePanel className="guild-forge-contract p-5 sm:p-6" accent="violet">
          <PanelHeading
            title="Founding charter"
            detail="These rules become the guild's starting economic contract. Review the live preview before queueing it."
          />

          <form onSubmit={handleSubmit} className="guild-forge-form grid gap-5">
            <CharterField
              label="Guild name"
              htmlFor={nameId}
              icon={<Crown size={16} aria-hidden="true" />}
              help="This is the banner other hunters see in the Guild Hall."
            >
              <input
                id={nameId}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="min-h-11 w-full px-3 py-2 text-sm"
                placeholder="Iron Covenant"
                maxLength={80}
                autoComplete="off"
              />
            </CharterField>

            <CharterField
              label="Publicly tradeable share"
              htmlFor={floatId}
              icon={<Percent size={16} aria-hidden="true" />}
              help="Use a decimal: 0.20 means 20%. The founder keeps the remaining shares. Maximum public float is 0.49."
            >
              <input
                id={floatId}
                type="number"
                min="0"
                max="0.49"
                step="0.01"
                value={publicFloatPct}
                onChange={(e) => setPublicFloatPct(e.target.value)}
                className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                inputMode="decimal"
              />
            </CharterField>

            <CharterField
              label="Dividend rule"
              htmlFor={policyId}
              icon={<Scale size={16} aria-hidden="true" />}
              help="Dividends pay guild-share owners from the guild treasury. They reduce the coin available for upkeep and investment."
            >
              <select
                id={policyId}
                value={dividendPolicy}
                onChange={(e) => setDividendPolicy(e.target.value)}
                className="min-h-11 w-full px-3 py-2 text-sm"
              >
                <option value="MANUAL">Leader decides each payment</option>
                <option value="AUTO_FIXED_PCT">Automatically pay a fixed treasury percentage</option>
              </select>
            </CharterField>

            {dividendPolicy === "AUTO_FIXED_PCT" && (
              <CharterField
                label="Automatic treasury share"
                htmlFor={autoDividendId}
                icon={<Landmark size={16} aria-hidden="true" />}
                help="Use a decimal: 0.10 pays 10% of the current guild treasury when the automatic policy runs."
              >
                <input
                  id={autoDividendId}
                  type="number"
                  min="0.01"
                  max="1"
                  step="0.01"
                  value={autoDividendPct}
                  onChange={(e) => setAutoDividendPct(e.target.value)}
                  className="min-h-11 w-full px-3 py-2 font-mono text-sm"
                  inputMode="decimal"
                />
              </CharterField>
            )}

            {errorMsg && (
              <div className="guild-forge-receipt flex items-start gap-2 border border-red-800 bg-red-900/20 px-3 py-2 text-sm text-red-300" role="alert">
                <AlertTriangle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                <span>{errorMsg}</span>
              </div>
            )}
            {successMsg && (
              <div className="guild-forge-receipt flex items-start gap-2 border border-green-800 bg-green-900/20 px-3 py-2 text-sm text-green-300" role="status">
                <CheckCircle2 size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                <span>{successMsg}</span>
              </div>
            )}

            <GameButton type="submit" disabled={submitIntent.isPending} className="w-full">
              <Sparkles size={17} aria-hidden="true" />
              {submitIntent.isPending ? "Queueing founding order…" : "Queue guild founding"}
            </GameButton>
          </form>
        </GamePanel>

        <GamePanel className="guild-forge-preview p-5 sm:p-6" accent="gold">
          <PanelHeading
            title="Charter preview"
            detail="What this configuration means in plain language."
          />
          <div className="guild-forge-preview-banner border border-[var(--line)] bg-black/10 p-4">
            <span className="game-eyebrow"><span className="game-eyebrow-rune" aria-hidden="true">◆</span> Proposed banner</span>
            <h2 className="mt-3 break-words text-xl uppercase">{name.trim() || "Unnamed Guild"}</h2>
          </div>
          <div className="guild-forge-preview-rules mt-3 grid gap-2" aria-label="Founding charter summary">
            <PreviewRule
              icon={<Crown size={17} aria-hidden="true" />}
              label="Founder control"
              value={`${Math.max(0, founderDisplay).toFixed(0)}% of starting shares`}
            />
            <PreviewRule
              icon={<Scale size={17} aria-hidden="true" />}
              label="Public market"
              value={`${Math.max(0, floatDisplay).toFixed(0)}% of shares tradeable`}
            />
            <PreviewRule
              icon={<Landmark size={17} aria-hidden="true" />}
              label="Rewards"
              value={dividendPolicy === "MANUAL"
                ? "Leader queues each dividend"
                : `${Math.max(0, autoVal * 100 || 0).toFixed(0)}% automatic treasury payment`}
            />
            <PreviewRule
              icon={<Clock3 size={17} aria-hidden="true" />}
              label="Activation"
              value="After the next completed world cycle"
            />
          </div>
          {!hasCreationFunds && (
            <div className="guild-forge-warning mt-4 border border-amber-800 bg-amber-900/15 p-3 text-sm text-amber-200">
              <strong className="block font-display uppercase">Cost not yet met</strong>
              <span className="mt-1 block text-xs text-amber-100/70">
                The command can be queued, but the world will reject it unless you have 50 available coin when the cycle resolves.
              </span>
            </div>
          )}
        </GamePanel>
      </div>
    </div>
  );
}

function CharterField({
  label,
  htmlFor,
  icon,
  help,
  children,
}: {
  label: string;
  htmlFor: string;
  icon: ReactNode;
  help: string;
  children: ReactNode;
}) {
  return (
    <div className="guild-forge-field grid gap-1.5">
      <label htmlFor={htmlFor} className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-[var(--parchment-soft)]">
        <span className="tone-gold">{icon}</span>
        {label}
      </label>
      {children}
      <p className="text-xs text-[var(--muted)]">{help}</p>
    </div>
  );
}

function PreviewRule({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="guild-forge-preview-rule grid grid-cols-[28px_1fr] gap-x-2 border border-[var(--line)] bg-black/10 p-3">
      <span className="row-span-2 tone-gold">{icon}</span>
      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{label}</span>
      <strong className="mt-0.5 text-sm font-medium text-[var(--parchment-soft)]">{value}</strong>
    </div>
  );
}
