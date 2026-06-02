import { Outlet, Link, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";
import { useRealtimeStore } from "../stores/realtime";
import { formatCurrency } from "../utils/format";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/gates", label: "Gates", icon: "castle" },
  { to: "/discover", label: "Discover", icon: "explore" },
  { to: "/orders", label: "Orders", icon: "receipt_long" },
  { to: "/guilds", label: "Guilds", icon: "groups" },
  { to: "/leaderboard", label: "Leaderboard", icon: "leaderboard" },
  { to: "/news", label: "News", icon: "newspaper" },
  { to: "/events", label: "Events", icon: "event" },
  { to: "/profile", label: "Profile", icon: "person" },
  { to: "/admin", label: "Admin", icon: "admin_panel_settings", adminOnly: true },
];

export default function Layout() {
  const { player, logout } = useAuthStore();
  const mode = useThemeStore((s) => s.mode);
  const toggleMode = useThemeStore((s) => s.toggleMode);
  const connectionState = useRealtimeStore((s) => s.connectionState);
  const navigate = useNavigate();
  const visibleNavItems = navItems.filter((item) =>
    item.adminOnly ? player?.role === "ADMIN" : true,
  );

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen">
      <nav className="hidden md:flex fixed left-0 top-0 h-full w-[260px] nm-sidebar px-4 py-8 flex-col z-40">
        <Link to="/dashboard" className="flex items-center gap-3 min-w-0 px-2 mb-8">
          <span className="dge-brand-mark shrink-0">
            DG
          </span>
          <span className="min-w-0">
            <span className="block text-lg font-semibold whitespace-nowrap overflow-hidden text-ellipsis">
              Dungeon Gate
            </span>
            <span className="block nm-soft-note text-xs font-mono uppercase">
              Economy Node v1.0.4
            </span>
          </span>
        </Link>

        <div className="flex flex-col gap-1 overflow-y-auto">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nm-nav-item text-sm transition-colors ${
                  isActive ? "nm-nav-item-active" : "nm-nav-item-idle"
                }`
              }
            >
              <span className="material-symbols-rounded text-xl">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <header className="fixed top-0 left-0 md:left-[260px] right-0 h-16 nm-topbar px-4 md:px-8 flex items-center justify-between gap-3 z-30">
        <Link to="/dashboard" className="md:hidden flex items-center gap-2 min-w-0">
          <span className="dge-brand-mark dge-brand-mark-sm shrink-0">DG</span>
          <span className="font-semibold truncate">Dungeon Gate</span>
        </Link>
        <div className="hidden md:flex items-center gap-3">
          <span className="text-xs px-3 py-1.5 rounded-full border border-gray-700 bg-gray-900 inline-flex items-center gap-2 font-mono uppercase">
            <span className="dge-status-dot" />
            WS {connectionState}
          </span>
        </div>

        {player && (
          <div className="flex items-center justify-end gap-2 md:gap-4 min-w-0">
            <span className="md:hidden text-xs px-2 py-1 rounded-full border border-gray-700 bg-gray-900 inline-flex items-center gap-2">
              <span className="dge-status-dot" />
              WS
            </span>
            <span className="hidden sm:inline text-sm text-gray-400 truncate max-w-36">
              {player.username}
            </span>
            {player.role === "ADMIN" && (
              <span
                className="hidden lg:inline text-xs px-2 py-0.5 rounded-full border"
                style={{
                  background: "rgba(241, 104, 88, 0.14)",
                  borderColor: "rgba(241, 104, 88, 0.5)",
                  color: "var(--nm-bad)",
                }}
              >
                ADMIN
              </span>
            )}
            <div className="text-sm font-mono text-brand-300 whitespace-nowrap px-3 py-1.5 border border-gray-800 bg-gray-900 rounded inline-flex items-center gap-1.5">
              <span className="material-symbols-rounded text-base">account_balance_wallet</span>
              ¤ {formatCurrency(player.balance_micro)}
            </div>
            <button
              onClick={toggleMode}
              className="text-sm text-gray-500 hover:text-gray-200 transition-colors px-2.5 py-1.5 rounded-md inline-flex items-center gap-1 border border-gray-800 bg-gray-900"
              title="Toggle theme"
            >
              <span className="material-symbols-rounded text-sm">
                {mode === "dark" ? "light_mode" : "dark_mode"}
              </span>
              <span className="hidden sm:inline">{mode === "dark" ? "Light" : "Dark"}</span>
            </button>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-200 transition-colors px-3 py-1.5 rounded-md border border-gray-800 bg-gray-900"
            >
              Logout
            </button>
          </div>
        )}
      </header>

      <div className="md:hidden fixed top-16 left-0 right-0 nm-mobile-nav px-3 py-2 flex gap-2 overflow-x-auto z-30">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-1 px-3 py-2 text-xs rounded-lg whitespace-nowrap border ${
                  isActive
                    ? "text-brand-700 bg-brand-100 border-brand-200"
                    : "text-gray-500 bg-gray-900 border-gray-800"
                }`
              }
            >
              <span className="material-symbols-rounded text-sm">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
      </div>

      <main className="relative z-10 pt-32 md:pt-24 pb-8 px-4 md:px-8 md:ml-[260px]">
        <Outlet />
      </main>
    </div>
  );
}
