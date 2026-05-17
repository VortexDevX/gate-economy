import { useAuthStore } from "../../stores/auth";
import { useSimulationStatus, useNews, useMyOrders } from "../../hooks/queries";
import {
  formatCurrency,
  formatCurrencyCompact,
  formatDate,
  shortId,
} from "../../utils/format";
import { Badge } from "../../components/StatusBadge";
import { Link } from "react-router-dom";

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
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="nm-page-title font-bold">Command Center</h1>
        <p className="nm-page-subtitle mt-1">
          Track your balance, open risk, and market movement in one view.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Your Balance"
          value={`¤ ${formatCurrency(player.balance_micro)}`}
        />
        <StatCard
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
          label="Treasury"
          value={
            simLoading
              ? "..."
              : `¤ ${formatCurrencyCompact(sim?.treasury_balance ?? 0)}`
          }
        />
        <StatCard
          label="Last Tick"
          value={
            sim?.last_completed_at ? formatDate(sim.last_completed_at) : "No completed tick yet"
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="nm-card rounded-xl p-6">
          <h2 className="nm-panel-title mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            <QuickLink to="/gates" label="Browse Gates" icon="hive" />
            <QuickLink to="/discover" label="Discover Gate" icon="travel_explore" />
            <QuickLink to="/orders" label="My Orders" icon="receipt_long" />
            <QuickLink to="/guilds" label="Guilds" icon="shield" />
            <QuickLink to="/news" label="News Feed" icon="newspaper" />
            <QuickLink to="/events" label="Events" icon="bolt" />
            <QuickLink to="/leaderboard" label="Leaderboard" icon="leaderboard" />
            <QuickLink to="/profile" label="Ledger" icon="account_balance_wallet" />
          </div>
        </div>

        <div className="nm-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="nm-panel-title">Latest News</h2>
            <Link to="/news" className="text-xs nm-action-link">
              Open feed →
            </Link>
          </div>
          {!newsData || newsData.items.length === 0 ? (
            <div className="nm-soft-note text-center py-6">
              No headlines yet. Run simulation ticks to generate market stories.
            </div>
          ) : (
            <ul className="space-y-2">
              {newsData.items.map((n) => (
                <li key={n.id} className="flex items-start gap-2 text-sm">
                  <span className="text-gray-500 shrink-0 text-xs mt-0.5">
                    T{n.tick_id}
                  </span>
                  <span className="text-gray-200">{n.headline}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="nm-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="nm-panel-title">Active Orders</h2>
            <Link to="/orders" className="text-xs nm-action-link">
              Manage orders →
            </Link>
          </div>
          {activeOrders.length === 0 ? (
            <div className="nm-soft-note text-center py-6">
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
  label,
  value,
  sub,
  subColor,
}: {
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
}) {
  return (
    <div className="nm-card rounded-xl p-4">
      <div className="nm-panel-title mb-1">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
      {sub && (
        <div className={`text-xs mt-1 ${subColor || "text-gray-500"}`}>
          {sub}
        </div>
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
      className="flex items-center gap-2.5 bg-gray-800 hover:bg-gray-800/50 border border-gray-700
                 rounded-lg px-3.5 py-2.5 text-sm text-gray-200 transition-colors"
    >
      <span className="nm-icon-chip">
        <span className="material-symbols-rounded text-base">{icon}</span>
      </span>
      <span>{label}</span>
    </Link>
  );
}

function PlaceholderSection({ title }: { title: string }) {
  return (
    <div className="nm-card rounded-xl p-6">
      <h2 className="nm-panel-title mb-4">{title}</h2>
      <div className="nm-soft-note text-center py-8">
        Portfolio analytics panel is being wired to holdings APIs.
      </div>
    </div>
  );
}

