type Variant =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "orange"
  | "yellow";

const variantStyles: Record<
  Variant,
  { background: string; border: string; color: string }
> = {
  green: {
    background: "rgba(56, 193, 114, 0.14)",
    border: "rgba(56, 193, 114, 0.48)",
    color: "var(--nm-good)",
  },
  blue: {
    background: "rgba(57, 208, 162, 0.12)",
    border: "rgba(57, 208, 162, 0.42)",
    color: "var(--nm-accent)",
  },
  amber: {
    background: "rgba(241, 179, 71, 0.16)",
    border: "rgba(241, 179, 71, 0.46)",
    color: "var(--nm-warn)",
  },
  red: {
    background: "rgba(241, 104, 88, 0.14)",
    border: "rgba(241, 104, 88, 0.48)",
    color: "var(--nm-bad)",
  },
  gray: {
    background: "rgba(184, 165, 131, 0.12)",
    border: "rgba(184, 165, 131, 0.36)",
    color: "var(--nm-muted)",
  },
  purple: {
    background: "rgba(141, 108, 255, 0.15)",
    border: "rgba(141, 108, 255, 0.44)",
    color: "#b9a7ff",
  },
  orange: {
    background: "rgba(217, 152, 62, 0.16)",
    border: "rgba(217, 152, 62, 0.48)",
    color: "var(--nm-primary-soft)",
  },
  yellow: {
    background: "rgba(255, 218, 112, 0.18)",
    border: "rgba(255, 218, 112, 0.5)",
    color: "#ffd66b",
  },
};

export function Badge({ label, variant }: { label: string; variant: Variant }) {
  const style = variantStyles[variant];
  return (
    <span
      className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full border"
      style={{
        background: style.background,
        borderColor: style.border,
        color: style.color,
        boxShadow: "inset 0 1px 0 rgba(255, 232, 178, 0.12)",
      }}
    >
      {label}
    </span>
  );
}

const gateStatusColors: Record<string, Variant> = {
  OFFERING: "blue",
  ACTIVE: "green",
  UNSTABLE: "amber",
  COLLAPSED: "red",
};

export function GateStatusBadge({ status }: { status: string }) {
  return <Badge label={status} variant={gateStatusColors[status] || "gray"} />;
}

const gateRankColors: Record<string, Variant> = {
  E: "gray",
  D: "green",
  C: "blue",
  B: "purple",
  A: "orange",
  S: "red",
  S_PLUS: "yellow",
};

export function GateRankBadge({ rank }: { rank: string }) {
  const display = rank === "S_PLUS" ? "S+" : rank;
  return <Badge label={display} variant={gateRankColors[rank] || "gray"} />;
}

const severityColors: Record<string, Variant> = {
  MINOR: "blue",
  MODERATE: "amber",
  MAJOR: "orange",
  CATASTROPHIC: "red",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <Badge label={severity} variant={severityColors[severity] || "gray"} />
  );
}
