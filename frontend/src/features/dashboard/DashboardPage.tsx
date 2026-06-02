import { Link } from "react-router-dom";
import { Badge } from "../../components/StatusBadge";
import { useSimulationStatus, useNews, useMyOrders } from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import {
  formatCurrency,
  formatCurrencyCompact,
  formatDate,
  shortId,
} from "../../utils/format";

type Variant =
  | "green"
  | "blue"
  | "amber"
  | "red"
  | "gray"
  | "purple"
  | "orange"
  | "yellow";

const orderStatusColors: Record<string, Variant> = {
  OPEN: "blue",
  PARTIAL: "amber",
  FILLED: "green",
  CANCELLED: "gray",
};

export default function DashboardPage() {
  const player = useAuthStore((s) => s.player);
  const { data: sim, isLoading: simLoading } = useSimulationStatus();
  const { data: newsData } = useNews({ limit: 5 });
  const { data: ordersData } = useMyOrders({ limit: 5 });

  if (!player) return null;

  const activeOrders =
    ordersData?.orders.filter(
      (o) => o.status === "OPEN" || o.status === "PARTIAL",
    ) ?? [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="mb-8">
        <h1 className="nm-page-title font-bold uppercase">Command Center</h1>
        <p className="nm-page-subtitle mt-2">
          Track your balance, open risk, and market movement in one view.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          code="#BAL-01"
          label="Your Balance"
          value={`¤ ${formatCurrency(player.balance_micro)}`}
          tone="gold"
        />
        <StatCard
          code="#SYS-TK"
          label="Simulation Tick"
          value={simLoading ? "..." : `#${sim?.current_tick ?? 0}`}
          sub={
            sim?.is_paused
              ? "Paused"
              : sim?.is_running
                ? "Running"
                : "Stopped"
          }
          subColor={
            sim?.is_paused
              ? "text-amber-400"
              : sim?.is_running
                ? "text-green-400"
                : "text-red-400"
          }
        />
        <StatCard
          code="#TRZ-GL"
          label="Treasury"
          value={
            simLoading
              ? "..."
              : `¤ ${formatCurrencyCompact(sim?.treasury_balance ?? 0)}`
          }
          tone="mana"
        />
        <StatCard
          code="#TM-STMP"
          label="Last Tick"
          value={
            sim?.last_completed_at
              ? formatDate(sim.last_completed_at)
              : "No completed tick yet"
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 nm-card rounded-xl p-6">
          <h2 className="nm-panel-title mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <QuickLink to="/gates" label="Browse Gates" icon="castle" />
            <QuickLink to="/discover" label="Discover Gate" icon="explore" />
            <QuickLink to="/orders" label="My Orders" icon="receipt_long" />
            <QuickLink to="/guilds" label="Guilds" icon="groups" />
            <QuickLink to="/news" label="News Feed" icon="newspaper" />
            <QuickLink to="/events" label="Events" icon="event" />
            <QuickLink to="/leaderboard" label="Leaderboard" icon="leaderboard" />
            <QuickLink to="/profile" label="Ledger" icon="account_balance" />
          </div>
        </div>

        <div className="nm-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="nm-panel-title">Latest News</h2>
            <Link to="/news" className="text-xs nm-action-link">
              Open feed →
            </Link>
          </div>
          {!newsData || newsData.items.length === 0 ? (
            <div className="nm-soft-note text-center py-10">
              No headlines yet. Run simulation ticks to generate market stories.
            </div>
          ) : (
            <ul className="space-y-3">
              {newsData.items.map((n) => (
                <li
                  key={n.id}
                  className="border border-gray-800 bg-gray-900 rounded-lg px-3 py-3 text-sm border-l-2"
                  style={{ borderLeftColor: "var(--nm-primary)" }}
                >
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <span>T{n.tick_id}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
                  </div>
                  <span className="text-gray-200 font-medium">{n.headline}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="nm-card rounded-xl p-6 min-h-[200px] flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="nm-panel-title">Active Orders</h2>
            <Link to="/orders" className="text-xs nm-action-link">
              Manage orders →
            </Link>
          </div>
          {activeOrders.length === 0 ? (
            <div className="nm-soft-note text-center py-12 flex-1 flex items-center justify-center">
              You have no active orders right now.
            </div>
          ) : (
            <ul className="space-y-2">
              {activeOrders.slice(0, 5).map((o) => (
                <li
                  key={o.id}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      label={o.side}
                      variant={o.side === "BUY" ? "green" : "red"}
                    />
                    <span className="font-mono text-xs text-gray-400">
                      {shortId(o.asset_id)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs">
                      {o.filled_quantity}/{o.quantity}
                    </span>
                    <Badge
                      label={o.status}
                      variant={orderStatusColors[o.status] || "gray"}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <PlaceholderSection title="Portfolio" />
      </div>
    </div>
  );
}

function StatCard({
  code,
  label,
  value,
  sub,
  subColor,
  tone = "plain",
}: {
  code: string;
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
  tone?: "plain" | "gold" | "mana";
}) {
  const valueTone =
    tone === "gold"
      ? "text-brand-300"
      : tone === "mana"
        ? "text-cyan-300"
        : "text-gray-200";

  return (
    <div className="nm-card rounded-xl p-6 relative overflow-hidden min-h-[150px]">
      <div className="absolute top-4 right-4 text-[10px] font-mono text-gray-500 opacity-70">
        {code}
      </div>
      <div className="nm-panel-title mb-4">{label}</div>
      <div className={`text-2xl font-mono font-bold ${valueTone}`}>{value}</div>
      {sub && (
        <div className={`text-xs mt-1 ${subColor || "text-gray-500"}`}>
          {sub}
        </div>
      )}
      {tone === "gold" && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-brand-400/30" />
      )}
    </div>
  );
}

function QuickLink({
  to,
  label,
  icon,
}: {
  to: string;
  label: string;
  icon: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-4 bg-gray-800 hover:bg-gray-800/50 border border-gray-700
                 rounded-lg px-4 py-3.5 text-sm text-gray-200 transition-colors"
    >
      <span className="material-symbols-rounded text-xl">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}

function PlaceholderSection({ title }: { title: string }) {
  return (
    <div className="nm-card rounded-xl p-6 min-h-[200px] flex flex-col relative overflow-hidden">
      <h2 className="nm-panel-title mb-6">{title}</h2>
      <div className="nm-soft-note text-center py-12 flex-1 flex items-center justify-center">
        Portfolio analytics panel is being wired to holdings APIs.
      </div>
    </div>
  );
}
