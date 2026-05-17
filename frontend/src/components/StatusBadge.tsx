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
    background: "linear-gradient(145deg, #e5faec, #d7f4e1)",
    border: "#b9e8ca",
    color: "#1c7a44",
  },
  blue: {
    background: "linear-gradient(145deg, #e6eeff, #d7e5ff)",
    border: "#bfd3ff",
    color: "#2558c7",
  },
  amber: {
    background: "linear-gradient(145deg, #fff5df, #ffefcf)",
    border: "#f4dcab",
    color: "#9f6a08",
  },
  red: {
    background: "linear-gradient(145deg, #ffe7e7, #ffdada)",
    border: "#f3b5b5",
    color: "#af2f2f",
  },
  gray: {
    background: "linear-gradient(145deg, #eef2f8, #e6ebf4)",
    border: "#d2dce9",
    color: "#52617c",
  },
  purple: {
    background: "linear-gradient(145deg, #f1e9ff, #e7dbff)",
    border: "#d6c1ff",
    color: "#6241b0",
  },
  orange: {
    background: "linear-gradient(145deg, #ffeedf, #ffe5d0)",
    border: "#f6cfa7",
    color: "#ab5e10",
  },
  yellow: {
    background: "linear-gradient(145deg, #fff8dd, #fff2c8)",
    border: "#f3e0a3",
    color: "#8f6f00",
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
        boxShadow:
          "4px 4px 9px rgba(156, 172, 196, 0.28), -3px -3px 9px rgba(255,255,255,0.9)",
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
