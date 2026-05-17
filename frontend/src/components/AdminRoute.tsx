import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export default function AdminRoute() {
  const player = useAuthStore((s) => s.player);
  if (!player || player.role !== "ADMIN") {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}
