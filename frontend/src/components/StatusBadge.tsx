type Variant =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "orange"
  | "yellow";

export function Badge({ label, variant }: { label: string; variant: Variant }) {
  return (
    <span className={`game-badge game-badge-${variant}`}>{label.replace(/_/g, " ")}</span>
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
