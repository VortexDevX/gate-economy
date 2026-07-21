import type { MarketHistoryPoint } from "../../api/types";
import LoadingSpinner from "../../components/LoadingSpinner";
import { formatCurrency } from "../../utils/format";

interface GatePulseProps {
  points: MarketHistoryPoint[] | undefined;
  stability: number;
  status: string;
  isLoading?: boolean;
  hasError?: boolean;
}

const WIDTH = 900;
const HEIGHT = 320;
const LEFT = 54;
const RIGHT = 28;
const TOP = 36;
const PRICE_BOTTOM = 214;
const VOLUME_TOP = 232;
const VOLUME_BOTTOM = 274;
const STABILITY_Y = 301;

export default function GatePulse({
  points,
  stability,
  status,
  isLoading = false,
  hasError = false,
}: GatePulseProps) {
  if (isLoading) {
    return <LoadingSpinner className="py-20" />;
  }

  if (hasError) {
    return (
      <div role="alert" className="nm-soft-note py-16 text-center">
        Gate pulse unavailable. Price history will retry on the next market refresh.
      </div>
    );
  }

  const ordered = [...(points ?? [])]
    .sort((a, b) => a.tick_number - b.tick_number)
    .slice(-60);

  if (ordered.length === 0) {
    return <DormantPulse stability={stability} status={status} />;
  }

  const lows = ordered.map((point) => point.low_micro);
  const highs = ordered.map((point) => point.high_micro);
  const rawMin = Math.min(...lows);
  const rawMax = Math.max(...highs);
  const rawRange = Math.max(rawMax - rawMin, 1);
  const priceMin = Math.max(0, rawMin - rawRange * 0.08);
  const priceMax = rawMax + rawRange * 0.08;
  const priceRange = Math.max(priceMax - priceMin, 1);
  const plotWidth = WIDTH - LEFT - RIGHT;
  const maxVolume = Math.max(...ordered.map((point) => point.volume_quantity), 1);
  const candleWidth = Math.max(2, Math.min(9, (plotWidth / ordered.length) * 0.46));

  const xFor = (index: number) =>
    ordered.length === 1
      ? LEFT + plotWidth / 2
      : LEFT + (index / (ordered.length - 1)) * plotWidth;
  const yFor = (price: number) =>
    PRICE_BOTTOM -
    ((price - priceMin) / priceRange) * (PRICE_BOTTOM - TOP);

  const closePoints = ordered
    .map((point, index) => `${xFor(index)},${yFor(point.close_micro)}`)
    .join(" ");
  const areaPoints = `${LEFT},${PRICE_BOTTOM} ${closePoints} ${xFor(ordered.length - 1)},${PRICE_BOTTOM}`;
  const first = ordered[0];
  const last = ordered[ordered.length - 1];
  const openingReference = first.open_micro || first.close_micro;
  const changePct = openingReference
    ? ((last.close_micro - openingReference) / openingReference) * 100
    : 0;
  const stabilityClamped = Math.max(0, Math.min(100, stability));
  const gaugeLeft = LEFT + 74;
  const gaugeWidth = WIDTH - RIGHT - gaugeLeft;
  const stabilityX = gaugeLeft + (stabilityClamped / 100) * gaugeWidth;
  const changeColor = changePct >= 0 ? "var(--nm-good)" : "var(--nm-bad)";

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="nm-panel-title">Gate Pulse</div>
          <p className="mt-1 text-xs text-gray-500">
            Executed price, tick volume, and current stability corridor.
          </p>
        </div>
        <div className="flex items-center gap-4 text-right font-mono text-xs">
          <div>
            <div className="text-gray-500">Last</div>
            <div className="text-base text-gray-200">
              ¤ {formatCurrency(last.close_micro)}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Window</div>
            <div className="text-base" style={{ color: changeColor }}>
              {changePct >= 0 ? "+" : ""}
              {changePct.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="block h-auto w-full min-w-[620px]"
        role="img"
        aria-labelledby="gate-pulse-title gate-pulse-description"
      >
        <title id="gate-pulse-title">Gate price and stability pulse</title>
        <desc id="gate-pulse-description">
          {`Price history from tick ${first.tick_number} to ${last.tick_number}. Last price ${formatCurrency(last.close_micro)}. Window change ${changePct.toFixed(2)} percent. Stability ${stabilityClamped.toFixed(1)} percent, status ${status}.`}
        </desc>
        <defs>
          <linearGradient id="gate-pulse-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--nm-accent)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--nm-accent)" stopOpacity="0" />
          </linearGradient>
          <filter id="gate-pulse-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {[0, 1, 2, 3, 4].map((step) => {
          const y = TOP + (step / 4) * (PRICE_BOTTOM - TOP);
          const price = priceMax - (step / 4) * priceRange;
          return (
            <g key={step}>
              <line
                x1={LEFT}
                x2={WIDTH - RIGHT}
                y1={y}
                y2={y}
                stroke="var(--nm-border)"
                strokeOpacity="0.35"
                strokeDasharray="3 8"
              />
              <text
                x={LEFT - 10}
                y={y + 4}
                textAnchor="end"
                fill="var(--nm-muted)"
                fontFamily="JetBrains Mono, monospace"
                fontSize="10"
              >
                {formatCurrency(Math.round(price))}
              </text>
            </g>
          );
        })}

        <polygon points={areaPoints} fill="url(#gate-pulse-area)" />

        {ordered.map((point, index) => {
          const x = xFor(index);
          const openY = yFor(point.open_micro);
          const closeY = yFor(point.close_micro);
          const highY = yFor(point.high_micro);
          const lowY = yFor(point.low_micro);
          const rising = point.close_micro >= point.open_micro;
          const color = rising ? "var(--nm-good)" : "var(--nm-bad)";
          const bodyY = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 1.5);
          const volumeHeight =
            (point.volume_quantity / maxVolume) * (VOLUME_BOTTOM - VOLUME_TOP);
          return (
            <g key={point.tick_number}>
              <line x1={x} x2={x} y1={highY} y2={lowY} stroke={color} strokeWidth="1" />
              <rect
                x={x - candleWidth / 2}
                y={bodyY}
                width={candleWidth}
                height={bodyHeight}
                rx="1"
                fill={color}
                opacity="0.9"
              />
              <rect
                x={x - Math.max(candleWidth / 2, 1)}
                y={VOLUME_BOTTOM - volumeHeight}
                width={Math.max(candleWidth, 2)}
                height={volumeHeight}
                fill={color}
                opacity="0.32"
              />
            </g>
          );
        })}

        <polyline
          points={closePoints}
          fill="none"
          stroke="var(--nm-accent)"
          strokeWidth="1.6"
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity="0.86"
        />
        <circle
          cx={xFor(ordered.length - 1)}
          cy={yFor(last.close_micro)}
          r="5"
          fill="var(--nm-accent)"
          stroke="var(--nm-surface)"
          strokeWidth="2"
          filter="url(#gate-pulse-glow)"
        />

        <text
          x={LEFT}
          y={VOLUME_TOP - 7}
          fill="var(--nm-muted)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
          letterSpacing="1.4"
        >
          EXECUTED VOLUME
        </text>
        <text
          x={LEFT}
          y={VOLUME_BOTTOM + 13}
          fill="var(--nm-muted)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
        >
          T{first.tick_number}
        </text>
        <text
          x={WIDTH - RIGHT}
          y={VOLUME_BOTTOM + 13}
          textAnchor="end"
          fill="var(--nm-muted)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
        >
          T{last.tick_number}
        </text>

        <text
          x={LEFT}
          y={STABILITY_Y + 4}
          fill="var(--nm-muted)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
        >
          STABILITY
        </text>
        <line
          x1={gaugeLeft}
          x2={gaugeLeft + gaugeWidth * 0.3}
          y1={STABILITY_Y}
          y2={STABILITY_Y}
          stroke="var(--nm-bad)"
          strokeWidth="6"
          strokeLinecap="round"
          opacity="0.64"
        />
        <line
          x1={gaugeLeft + gaugeWidth * 0.3}
          x2={gaugeLeft + gaugeWidth * 0.6}
          y1={STABILITY_Y}
          y2={STABILITY_Y}
          stroke="var(--nm-warn)"
          strokeWidth="6"
          opacity="0.64"
        />
        <line
          x1={gaugeLeft + gaugeWidth * 0.6}
          x2={WIDTH - RIGHT}
          y1={STABILITY_Y}
          y2={STABILITY_Y}
          stroke="var(--nm-good)"
          strokeWidth="6"
          strokeLinecap="round"
          opacity="0.64"
        />
        <path
          d={`M ${stabilityX} ${STABILITY_Y - 10} l -5 -7 h 10 z`}
          fill="var(--nm-primary)"
        />
        <text
          x={WIDTH - RIGHT}
          y={STABILITY_Y - 10}
          textAnchor="end"
          fill="var(--nm-primary-soft)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="10"
        >
          {stabilityClamped.toFixed(1)}% · {status}
        </text>
      </svg>
    </div>
  );
}

function DormantPulse({ stability, status }: { stability: number; status: string }) {
  const clamped = Math.max(0, Math.min(100, stability));
  return (
    <div className="py-6">
      <div className="mb-3">
        <div className="nm-panel-title">Gate Pulse</div>
        <p className="mt-1 text-xs text-gray-500">
          No executed history yet. Pulse begins with first matched trade.
        </p>
      </div>
      <svg
        viewBox="0 0 900 210"
        className="block h-auto w-full min-w-[620px]"
        role="img"
        aria-label={`No executed trade history. Current gate stability ${clamped.toFixed(1)} percent, status ${status}.`}
      >
        <line
          x1="54"
          x2="872"
          y1="105"
          y2="105"
          stroke="var(--nm-border)"
          strokeDasharray="4 10"
          opacity="0.6"
        />
        <path
          d="M54 105 H330 L348 105 L358 78 L372 132 L386 105 H872"
          fill="none"
          stroke="var(--nm-accent)"
          strokeWidth="2"
          opacity="0.72"
        />
        <text
          x="450"
          y="166"
          textAnchor="middle"
          fill="var(--nm-muted)"
          fontFamily="JetBrains Mono, monospace"
          fontSize="11"
        >
          AWAITING FIRST EXECUTION · STABILITY {clamped.toFixed(1)}%
        </text>
      </svg>
    </div>
  );
}
