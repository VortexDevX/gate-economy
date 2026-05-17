import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export default function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping } = useAuthStore();

  if (isBootstrapping) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
