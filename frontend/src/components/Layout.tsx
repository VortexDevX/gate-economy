import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Aperture,
  BookOpen,
  ChevronRight,
  CircleUserRound,
  Compass,
  Crown,
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

const DISMISSED_QUEST_KEY = "dge_dismissed_quest";

interface NavItem {
  to: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

const primaryNavigation: NavItem[] = [
  { to: "/dashboard", label: "Sanctum", shortLabel: "Home", icon: Compass },
  { to: "/discover", label: "Expeditions", shortLabel: "Scout", icon: Sparkles },
  { to: "/gates", label: "Gate Market", shortLabel: "Market", icon: Aperture },
  { to: "/guilds", label: "Guilds", shortLabel: "Guilds", icon: Shield },
  { to: "/leaderboard", label: "Season", shortLabel: "Season", icon: Trophy },
];

const utilityNavigation: NavItem[] = [
  { to: "/orders", label: "Orders & Results", shortLabel: "Orders", icon: ReceiptText },
  { to: "/news", label: "Realm Dispatches", shortLabel: "News", icon: Newspaper },
  { to: "/events", label: "Active Omens", shortLabel: "Omens", icon: Radio },
  { to: "/profile", label: "Hunter Vault", shortLabel: "Vault", icon: CircleUserRound },
  { to: "/guide", label: "Field Guide", shortLabel: "Guide", icon: BookOpen },
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

  const utilities = utilityNavigation.filter((item) => !item.adminOnly || player?.role === "ADMIN");
  const worldOnline = Boolean(simulation?.is_running && !simulation?.is_paused);
  const questProgress = (portfolio?.gate_positions.length ?? 0) > 0 ? 2 : 0;
  const questId = questProgress > 0 ? "build-first-position" : "discover-first-gate";
  const questStorageKey = `${DISMISSED_QUEST_KEY}:${player?.id ?? "guest"}`;
  const [dismissedQuest, setDismissedQuest] = useState<string | null>(() =>
    localStorage.getItem(questStorageKey),
  );

  useEffect(() => {
    setDismissedQuest(localStorage.getItem(questStorageKey));
  }, [questStorageKey]);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    document.body.classList.add("drawer-open");
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.classList.remove("drawer-open");
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileMenuOpen]);

  const handleLogout = () => {
    logout();
    queryClient.clear();
    navigate("/login", { replace: true });
  };

  const dismissQuest = () => {
    localStorage.setItem(questStorageKey, questId);
    setDismissedQuest(questId);
  };

  return (
    <div className="game-shell realm-shell">
      <div className="realm-backdrop" aria-hidden="true" />
      <div className="realm-atmosphere" aria-hidden="true"><i /><i /><i /></div>

      <header className="realm-hud">
        <button
          className="realm-icon-button realm-menu-trigger"
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open navigation"
        >
          <Menu size={21} aria-hidden="true" />
        </button>

        <BrandLockup />

        <nav className="realm-primary-nav" aria-label="Main game areas">
          {primaryNavigation.map((item) => <TopNavItem key={item.to} item={item} />)}
        </nav>

        <div className="realm-hud-right">
          <div className={`realm-cycle ${worldOnline ? "is-live" : "is-halted"}`}>
            <span className="realm-cycle-pulse" aria-hidden="true" />
            <span>{worldOnline ? "Realm live" : "Realm paused"}</span>
            <strong>Cycle {simulation?.current_tick ?? 0}</strong>
          </div>
          <div className="realm-resource realm-resource-worth">
            <History size={15} aria-hidden="true" />
            <span>Worth</span>
            <strong>{formatCurrency(portfolio?.net_worth_micro ?? player?.balance_micro ?? 0)}</strong>
          </div>
          <div className="realm-resource realm-resource-coin">
            <WalletCards size={15} aria-hidden="true" />
            <span>Coin</span>
            <strong>{formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}</strong>
          </div>
          <div
            className={`realm-feed realm-feed-${connectionState}`}
            role="img"
            aria-label={`World feed ${connectionState}`}
            title={`World feed: ${connectionState}`}
          >
            <Radio size={17} aria-hidden="true" />
          </div>
          <button
            className="realm-icon-button realm-theme"
            onClick={toggleMode}
            aria-label={`Switch to ${mode === "dark" ? "daylight" : "night"} mode`}
            title={`Switch to ${mode === "dark" ? "daylight" : "night"} mode`}
          >
            {mode === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
        </div>
      </header>

      <aside className="realm-utility-rail" aria-label="Hunter tools">
        {utilities.map((item) => <RailNavItem key={item.to} item={item} />)}
        <span className="realm-rail-spacer" />
        <button onClick={handleLogout} className="realm-rail-item realm-rail-logout" aria-label="Leave exchange">
          <LogOut size={19} aria-hidden="true" />
          <span>Leave exchange</span>
        </button>
      </aside>

      {!worldOnline && (
        <div className="realm-pause-notice" role="status">
          <span className="pause-crystal" aria-hidden="true" />
          <div><strong>Time stands still</strong><span>Commands are safe. Realm must resume before they resolve.</span></div>
        </div>
      )}

      {dismissedQuest !== questId && (
        <div className="realm-quest-beacon" role="status">
          <Link to={questProgress > 0 ? "/profile" : "/discover"} className="quest-beacon-link">
            <span className="quest-beacon-icon"><Compass size={19} aria-hidden="true" /></span>
            <span className="quest-beacon-copy">
              <small>Active quest · {questProgress}/4</small>
              <strong>{questProgress > 0 ? "Build your first position" : "Discover your first gate"}</strong>
            </span>
            <ChevronRight size={17} aria-hidden="true" />
          </Link>
          <button className="quest-beacon-dismiss" onClick={dismissQuest} aria-label="Dismiss active quest">
            <X size={15} aria-hidden="true" />
          </button>
        </div>
      )}

      <main className={`game-stage realm-stage ${!worldOnline ? "realm-stage-paused" : ""}`}>
        <Outlet />
      </main>

      <nav className="realm-mobile-dock" aria-label="Mobile game navigation">
        {primaryNavigation.slice(0, 4).map((item) => <MobileNavItem key={item.to} item={item} />)}
        <button onClick={() => setMobileMenuOpen(true)} className="realm-mobile-dock-item">
          <Menu size={21} aria-hidden="true" /><span>More</span>
        </button>
      </nav>

      {mobileMenuOpen && (
        <div className="realm-drawer-layer" role="presentation" onClick={() => setMobileMenuOpen(false)}>
          <section
            className="realm-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Game navigation"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="realm-drawer-head">
              <BrandLockup compact />
              <button className="realm-icon-button" onClick={() => setMobileMenuOpen(false)} aria-label="Close navigation">
                <X size={21} aria-hidden="true" />
              </button>
            </div>
            <div className="realm-drawer-player">
              <div><small>Signed in as</small><strong>{player?.username ?? "Hunter"}</strong></div>
              <span>¤ {formatCurrency(portfolio?.cash_balance_micro ?? player?.balance_micro ?? 0)}</span>
            </div>
            <nav className="realm-drawer-nav">
              {[...primaryNavigation, ...utilities].map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/dashboard"}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) => `realm-drawer-link ${isActive ? "is-active" : ""}`}
                >
                  <span className="drawer-link-icon"><item.icon size={19} aria-hidden="true" /></span>
                  <span><strong>{item.label}</strong><small>{navDescription(item.to)}</small></span>
                  <ChevronRight size={16} aria-hidden="true" />
                </NavLink>
              ))}
            </nav>
            <button className="realm-drawer-theme" onClick={toggleMode}>
              {mode === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
              Switch to {mode === "dark" ? "daylight" : "night"} mode
            </button>
            <button className="realm-drawer-logout" onClick={handleLogout}>
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
    <Link to="/dashboard" className={`realm-brand ${compact ? "is-compact" : ""}`} aria-label="Dungeon Gate home">
      <span className="realm-brand-sigil" aria-hidden="true"><span /><Aperture size={27} /></span>
      <span className="realm-brand-copy"><strong>DUNGEON GATE</strong><small>REALM EXCHANGE</small></span>
    </Link>
  );
}

function TopNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink to={item.to} end={item.to === "/dashboard"} className={({ isActive }) => `realm-tab ${isActive ? "is-active" : ""}`}>
      <item.icon size={17} aria-hidden="true" />
      <span>{item.label}</span>
      <i aria-hidden="true" />
    </NavLink>
  );
}

function RailNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink to={item.to} className={({ isActive }) => `realm-rail-item ${isActive ? "is-active" : ""}`} aria-label={item.label}>
      <item.icon size={19} aria-hidden="true" />
      <span>{item.label}</span>
    </NavLink>
  );
}

function MobileNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink to={item.to} end={item.to === "/dashboard"} className={({ isActive }) => `realm-mobile-dock-item ${isActive ? "is-active" : ""}`}>
      <item.icon size={21} aria-hidden="true" /><span>{item.shortLabel}</span>
    </NavLink>
  );
}

function navDescription(path: string): string {
  const descriptions: Record<string, string> = {
    "/dashboard": "Choose your next move",
    "/discover": "Fund a gate expedition",
    "/gates": "Trade living dungeon assets",
    "/guilds": "Build shared power",
    "/leaderboard": "Climb current season",
    "/orders": "Track commands and trades",
    "/news": "Read market-changing reports",
    "/events": "Watch dangerous modifiers",
    "/profile": "Inspect wealth and holdings",
    "/guide": "Learn rules and first moves",
    "/admin": "Operate realm systems",
  };
  return descriptions[path] ?? "Open game area";
}
