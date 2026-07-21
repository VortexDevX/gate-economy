import { useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import AdminRoute from "../components/AdminRoute";
import Layout from "../components/Layout";
import LoginPage from "../features/auth/LoginPage";
import RegisterPage from "../features/auth/RegisterPage";
import DashboardPage from "../features/dashboard/DashboardPage";
import GatesListPage from "../features/gates/GatesListPage";
import GateDetailPage from "../features/gates/GateDetailPage";
import DiscoverPage from "../features/gates/DiscoverPage";
import ProfilePage from "../features/profile/ProfilePage";
import NewsPage from "../features/news/NewsPage";
import EventsPage from "../features/events/EventsPage";
import OrdersPage from "../features/orders/OrdersPage";
import GuildsListPage from "../features/guilds/GuildsListPage";
import GuildDetailPage from "../features/guilds/GuildDetailPage";
import CreateGuildPage from "../features/guilds/CreateGuildPage";
import LeaderboardPage from "../features/leaderboard/LeaderboardPage";
import AdminPage from "../features/admin/AdminPage";
import GuidePage from "../features/guide/GuidePage";

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}

export default function AppRoutes() {
  return (
    <>
      <ScrollToTop />
      <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/gates" element={<GatesListPage />} />
          <Route path="/gates/:gateId" element={<GateDetailPage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/guilds" element={<GuildsListPage />} />
          <Route path="/guilds/create" element={<CreateGuildPage />} />
          <Route path="/guilds/:guildId" element={<GuildDetailPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/news" element={<NewsPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/guide" element={<GuidePage />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminPage />} />
          </Route>
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  );
}
