import { Outlet, Link, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";
import { useRealtimeStore } from "../stores/realtime";
import { formatCurrency } from "../utils/format";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "space_dashboard" },
  { to: "/gates", label: "Gates", icon: "hive" },
  { to: "/discover", label: "Discover", icon: "travel_explore" },
  { to: "/orders", label: "Orders", icon: "receipt_long" },
  { to: "/guilds", label: "Guilds", icon: "shield" },
  { to: "/leaderboard", label: "Leaderboard", icon: "leaderboard" },
  { to: "/news", label: "News", icon: "newspaper" },
  { to: "/events", label: "Events", icon: "bolt" },
  { to: "/profile", label: "Profile", icon: "account_circle" },
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
    <div className="min-h-screen flex flex-col px-3 md:px-5 py-3 md:py-4 gap-4">
      {/* Top nav */}
      <header className="nm-shell px-6 py-4 flex items-center justify-between rounded-2xl">
        <Link to="/dashboard" className="flex items-center gap-3 min-w-0">
          <span className="w-10 h-10 rounded-xl bg-brand-600 text-white font-bold text-base inline-flex items-center justify-center">
            DG
          </span>
          <span className="text-xl md:text-[1.65rem] font-semibold tracking-tight whitespace-nowrap overflow-hidden text-ellipsis">
            Dungeon Gate Economy
          </span>
        </Link>

        {player && (
          <div className="flex items-center gap-4">
            <span className="text-xs px-2 py-1 rounded-full border border-gray-700 bg-gray-900">
              WS: {connectionState}
            </span>
            <button
              onClick={toggleMode}
              className="text-sm text-gray-500 hover:text-gray-200 transition-colors px-2 py-1 rounded-md inline-flex items-center gap-1"
            >
              <span className="material-symbols-rounded text-sm">
                {mode === "dark" ? "light_mode" : "dark_mode"}
              </span>
              {mode === "dark" ? "Light" : "Dark"}
            </button>
            <div className="text-sm flex items-center gap-2">
              <span className="text-gray-400 mr-2">{player.username}</span>
              {player.role === "ADMIN" && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full mr-2 border"
                  style={{
                    background: "linear-gradient(145deg, #ffe6e6, #ffdada)",
                    borderColor: "#f3b1b1",
                    color: "#9b2c2c",
                  }}
                >
                  ADMIN
                </span>
              )}
            </div>
            <div className="text-sm font-mono text-brand-300 whitespace-nowrap">
              ¤ {formatCurrency(player.balance_micro)}
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-200 transition-colors px-2 py-1 rounded-md"
            >
              Logout
            </button>
          </div>
        )}
      </header>

      <div className="flex flex-1 gap-4">
        {/* Sidebar */}
        <nav className="w-64 nm-sidebar py-4 px-2 shrink-0 hidden md:block rounded-2xl">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nm-nav-item mx-1.5 my-1 text-sm transition-colors ${
                  isActive
                    ? "nm-nav-item-active"
                    : "nm-nav-item-idle"
                }`
              }
            >
              <span className="nm-icon-chip">
                <span className="material-symbols-rounded text-base">{item.icon}</span>
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Mobile nav */}
        <div className="md:hidden nm-sidebar px-2 py-2 flex gap-1 overflow-x-auto rounded-xl">
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

        {/* Main content */}
        <main className="flex-1 p-6 md:p-7 overflow-auto nm-main rounded-2xl">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
