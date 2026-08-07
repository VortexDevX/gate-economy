import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CircleHelp, Sparkles } from "lucide-react";

export type GameTone = "gold" | "aether" | "good" | "warn" | "danger" | "violet" | "muted";

export function GamePanel({
  children,
  className = "",
  accent = "gold",
}: {
  children: ReactNode;
  className?: string;
  accent?: GameTone;
}) {
  return (
    <section className={`game-panel game-panel-${accent} ${className}`}>
      <span className="game-panel-corner game-panel-corner-a" aria-hidden="true" />
      <span className="game-panel-corner game-panel-corner-b" aria-hidden="true" />
      {children}
    </section>
  );
}

export function ScreenHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="game-screen-header">
      <div className="min-w-0">
        <div className="game-eyebrow">
          <Sparkles className="game-eyebrow-rune" size={13} aria-hidden="true" />
          {eyebrow}
        </div>
        <h1 className="game-screen-title">{title}</h1>
        <p className="game-screen-copy">{description}</p>
      </div>
      {action && <div className="game-screen-action">{action}</div>}
    </header>
  );
}

export function PanelHeading({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="game-panel-heading">
      <div>
        <h2>{title}</h2>
        {detail && <p>{detail}</p>}
      </div>
      {action}
    </div>
  );
}

export function RankCrest({ rank, size = "md" }: { rank: string; size?: "sm" | "md" | "lg" }) {
  const label = rank === "S_PLUS" ? "S+" : rank;
  return (
    <span
      className={`rank-crest rank-${rank.toLowerCase()} rank-crest-${size}`}
      role="img"
      aria-label={`Rank ${label}`}
    >
      <span aria-hidden="true">{label}</span>
    </span>
  );
}

export function StabilityMeter({
  value,
  threshold,
  compact = false,
}: {
  value: number;
  threshold?: number;
  compact?: boolean;
}) {
  const safeValue = Math.max(0, Math.min(100, value));
  const tone = safeValue <= 30 ? "danger" : safeValue <= 60 ? "warn" : "good";
  return (
    <div className={`stability-meter ${compact ? "stability-meter-compact" : ""}`}>
      <div className="stability-meter-label">
        <span>Gate stability</span>
        <strong className={`tone-${tone}`}>{safeValue.toFixed(1)}%</strong>
      </div>
      <div className="stability-meter-track" aria-label={`Gate stability ${safeValue.toFixed(1)} percent`}>
        <div className={`stability-meter-fill tone-bg-${tone}`} style={{ width: `${safeValue}%` }} />
        {threshold != null && (
          <span
            className="stability-meter-threshold"
            style={{ left: `${Math.max(0, Math.min(100, threshold))}%` }}
            title={`Collapse threshold ${threshold}%`}
          />
        )}
      </div>
      {!compact && threshold != null && (
        <div className="stability-meter-foot">
          <span>Collapse line</span>
          <span>{Math.max(0, value - threshold).toFixed(1)} points of safety</span>
        </div>
      )}
    </div>
  );
}

export function StatRune({
  label,
  value,
  note,
  tone = "muted",
  icon,
}: {
  label: string;
  value: string;
  note?: string;
  tone?: GameTone;
  icon?: ReactNode;
}) {
  return (
    <article className={`stat-rune stat-rune-${tone}`}>
      <div className="stat-rune-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

export function GameAction({
  to,
  children,
  tone = "primary",
  className = "",
}: {
  to: string;
  children: ReactNode;
  tone?: "primary" | "secondary" | "ghost" | "danger";
  className?: string;
}) {
  return (
    <Link to={to} className={`game-action game-action-${tone} ${className}`}>
      <span>{children}</span>
      <ArrowRight size={17} aria-hidden="true" />
    </Link>
  );
}

export function GameEmpty({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: { to: string; label: string };
}) {
  return (
    <div className="game-empty">
      <span className="game-empty-sigil" aria-hidden="true"><Sparkles size={24} /></span>
      <h3>{title}</h3>
      <p>{message}</p>
      {action && <GameAction to={action.to}>{action.label}</GameAction>}
    </div>
  );
}

export function PlainTip({ children }: { children: ReactNode }) {
  return (
    <div className="plain-tip">
      <CircleHelp size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}

export function GameButton({
  children,
  type = "button",
  tone = "primary",
  disabled = false,
  onClick,
  className = "",
}: {
  children: ReactNode;
  type?: "button" | "submit";
  tone?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`game-button game-button-${tone} ${className}`}
    >
      {children}
    </button>
  );
}
