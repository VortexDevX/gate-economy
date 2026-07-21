import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Aperture,
  BookOpen,
  ChevronRight,
  CircleUserRound,
  Compass,
  Crown,
  DoorOpen,
  History,
  LogOut,
  Menu,
  Moon,
  Newspaper,
  Radio,
  ReceiptText,
  Shield,
  Sparkles,
  Sun,
  Trophy,
  WalletCards,
  X,
  type LucideIcon,
} from "lucide-react";
import { useMyPortfolio, useSimulationStatus } from "../hooks/queries";
import { useAuthStore } from "../stores/auth";
import { useRealtimeStore } from "../stores/realtime";
import { useThemeStore } from "../stores/theme";
import { formatCurrency } from "../utils/format";

interface NavItem {
  to: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

const primaryNavigation: NavItem[] = [
  { to: "/dashboard", label: "Command Chamber", shortLabel: "Command", icon: Compass },
  { to: "/discover", label: "Launch Expedition", shortLabel: "Discover", icon: Sparkles },
  { to: "/gates", label: "Gate Atlas", shortLabel: "Gates", icon: Aperture },
  { to: "/guilds", label: "Guild Hall", shortLabel: "Guilds", icon: Shield },
  { to: "/leaderboard", label: "Season Crown", shortLabel: "Season", icon: Trophy },
];

const secondaryNavigation: NavItem[] = [
  { to: "/orders", label: "Orders & Results", shortLabel: "Orders", icon: ReceiptText },
  { to: "/news", label: "World Dispatches", shortLabel: "Dispatches", icon: Newspaper },
  { to: "/events", label: "Active Omens", shortLabel: "Events", icon: Radio },
  { to: "/profile", label: "Hunter Chronicle", shortLabel: "Profile", icon: CircleUserRound },
  { to: "/guide", label: "How to Play", shortLabel: "Guide", icon: BookOpen },
  { to: "/admin", label: "Keeper Console", shortLabel: "Admin", icon: Crown, adminOnly: true },
];

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { player, logout } = useAuthStore();
  const mode = useThemeStore((state) => state.mode);
  const toggleMode = useThemeStore((state) => state.toggleMode);
  const connectionState = useRealtimeStore((state) => state.connectionState);
  const { data: simulation } = useSimulationStatus();
  const { data: portfolio } = useMyPortfolio();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const secondaries = secondaryNavigation.filter((item) =>
    item.adminOnly ? player?.role === "ADMIN" : true,
  );
  const worldOnline = simulation?.is_running && !simulation?.is_paused;
  const firstQuestComplete = (portfolio?.gate_positions.length ?? 0) > 0;

  const handleLogout = () => {
    logout();
    queryClient.clear();
    navigate("/login", { replace: true });
  };

  return (
    <div className="game-shell">
      <aside className="game-sidebar" aria-label="Primary navigation">
        <BrandLockup />

        <nav className="game-nav" aria-label="Play">
          <div className="game-nav-label">Play</div>
          {primaryNavigation.map((item) => <DesktopNavItem key={item.to} item={item} />)}
        </nav>

        <nav className="game-nav game-nav-secondary" aria-label="Field kit">
          <div className="game-nav-label">Field kit</div>
          {secondaries.map((item) => <DesktopNavItem key={item.to} item={item} />)}
        </nav>

        <Link to={firstQuestComplete ? "/profile" : "/discover"} className="sidebar-quest">
          <div className="sidebar-quest-head">
            <span>Current quest</span>
            <span>{firstQuestComplete ? "2/4" : "0/4"}</span>
          </div>
          <strong>{firstQuestComplete ? "Build your first position" : "Find your first gate"}</strong>
          <p>
            {firstQuestComplete
              ? "Inspect your holding, then decide whether to hold for yield or trade."
              : "Start with an E-rank expedition. It is the cheapest way into the economy."}
          </p>
          <span className="sidebar-quest-action">
            {firstQuestComplete ? "View chronicle" : "Begin expedition"}
            <ChevronRight size={14} aria-hidden="true" />
          </span>
        </Link>
      </aside>

      <header className="game-topbar">
        <div className="game-topbar-left">
          <button
            className="game-icon-button game-mobile-menu-button"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} aria-hidden="true" />
          </button>
          <Link to="/dashboard" className="game-mobile-brand" aria-label="Obsidian Exchange home">
            <span className="brand-sigil brand-sigil-small"><Aperture size={19} aria-hidden="true" /></span>
            <span>OBSIDIAN EXCHANGE</span>
          </Link>
          <div className={`world-state ${worldOnline ? "world-state-live" : "world-state-offline"}`}>
            <span className="world-state-dot" aria-hidden="true" />
            <span>{worldOnline ? "World live" : "World halted"}</span>
            <strong>Cycle {simulation?.current_tick ?? 0}</strong>
          </div>
        </div>

        <div className="game-resources" aria-label="Player resources">
          <div className="resource-chip resource-chip-worth">
            <History size={15} aria-hidden="true" />
            <span>Worth</span>
            <strong>¤ {formatCurrency(portfolio?.net_worth_micro ?? player?.balance_micro ?? 0)}</strong>
          </div>
          <div className="resource-chip">
            <WalletCards size={15} aria-hidden="true" />
            <span>Coin</span>
            <strong>¤ {formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}</strong>
          </div>
          <div
            className={`connection-rune connection-${connectionState}`}
            title={`World feed: ${connectionState}`}
            role="img"
            aria-label={`World feed ${connectionState}`}
          >
            <Radio size={16} aria-hidden="true" />
          </div>
          <button
            onClick={toggleMode}
            className="game-icon-button game-theme-button"
            aria-label={`Switch to ${mode === "dark" ? "torchlight" : "void"} theme`}
          >
            {mode === "dark" ? <Sun size={17} aria-hidden="true" /> : <Moon size={17} aria-hidden="true" />}
          </button>
          <button onClick={handleLogout} className="game-icon-button" aria-label="Leave the exchange">
            <LogOut size={17} aria-hidden="true" />
          </button>
        </div>
      </header>

      {!worldOnline && (
        <div className="world-halted-banner" role="status">
          <DoorOpen size={17} aria-hidden="true" />
          <strong>The world engine is halted.</strong>
          <span>Orders and expeditions can be prepared, but nothing resolves until the simulation worker starts.</span>
        </div>
      )}

      <main className={`game-stage ${!worldOnline ? "game-stage-with-banner" : ""}`}>
        <Outlet />
      </main>

      <nav className="game-mobile-dock" aria-label="Mobile play navigation">
        {primaryNavigation.slice(0, 4).map((item) => <MobileNavItem key={item.to} item={item} />)}
        <button onClick={() => setMobileMenuOpen(true)} className="game-mobile-dock-item">
          <Menu size={20} aria-hidden="true" />
          <span>More</span>
        </button>
      </nav>

      {mobileMenuOpen && (
        <div className="mobile-drawer-layer" role="presentation" onClick={() => setMobileMenuOpen(false)}>
          <section
            className="mobile-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mobile-drawer-head">
              <BrandLockup compact />
              <button className="game-icon-button" onClick={() => setMobileMenuOpen(false)} aria-label="Close navigation">
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <div className="mobile-drawer-player">
              <span>{player?.username ?? "Hunter"}</span>
              <strong>¤ {formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}</strong>
            </div>
            <nav className="mobile-drawer-nav">
              {[...primaryNavigation, ...secondaries].map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/dashboard"}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) => `mobile-drawer-link ${isActive ? "is-active" : ""}`}
                >
                  <item.icon size={19} aria-hidden="true" />
                  <span>{item.label}</span>
                  <ChevronRight size={15} aria-hidden="true" />
                </NavLink>
              ))}
            </nav>
            <button className="mobile-drawer-logout" onClick={handleLogout}>
              <LogOut size={18} aria-hidden="true" /> Leave exchange
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

function BrandLockup({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/dashboard" className={`game-brand ${compact ? "game-brand-compact" : ""}`}>
      <span className="brand-sigil"><Aperture size={25} aria-hidden="true" /></span>
      <span>
        <strong>Dungeon Gate</strong>
        <small>The Obsidian Exchange</small>
      </span>
    </Link>
  );
}

function DesktopNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === "/dashboard"}
      className={({ isActive }) => `game-nav-item ${isActive ? "is-active" : ""}`}
    >
      <item.icon size={18} aria-hidden="true" />
      <span>{item.label}</span>
      <i aria-hidden="true" />
    </NavLink>
  );
}

function MobileNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === "/dashboard"}
      className={({ isActive }) => `game-mobile-dock-item ${isActive ? "is-active" : ""}`}
    >
      <item.icon size={20} aria-hidden="true" />
      <span>{item.shortLabel}</span>
    </NavLink>
  );
}
