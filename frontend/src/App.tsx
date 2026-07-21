import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "./stores/auth";
import { useThemeStore } from "./stores/theme";
import { useRealtimeStore } from "./stores/realtime";
import { useMe } from "./hooks/queries";
import AppRoutes from "./routes";

export default function App() {
  const queryClient = useQueryClient();
  const bootstrapAuth = useAuthStore((s) => s.bootstrap);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const syncPlayer = useAuthStore((s) => s.syncPlayer);
  const bootstrapTheme = useThemeStore((s) => s.bootstrap);
  const connectRealtime = useRealtimeStore((s) => s.connect);
  const disconnectRealtime = useRealtimeStore((s) => s.disconnect);
  const { data: playerSnapshot } = useMe(isAuthenticated);

  useEffect(() => {
    bootstrapTheme();
    bootstrapAuth();
  }, [bootstrapTheme, bootstrapAuth]);

  useEffect(() => {
    if (isAuthenticated && playerSnapshot) {
      syncPlayer(playerSnapshot);
    }
  }, [isAuthenticated, playerSnapshot, syncPlayer]);

  useEffect(() => {
    if (!isAuthenticated) {
      disconnectRealtime();
      return;
    }
    connectRealtime(() => {
      queryClient.invalidateQueries({ queryKey: ["simulation", "status"] });
      queryClient.invalidateQueries({ queryKey: ["news"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["market"] });
      queryClient.invalidateQueries({ queryKey: ["orders", "me"] });
      queryClient.invalidateQueries({ queryKey: ["intents", "me"] });
      queryClient.invalidateQueries({ queryKey: ["players", "me"] });
      queryClient.invalidateQueries({ queryKey: ["gates"] });
      queryClient.invalidateQueries({ queryKey: ["guilds"] });
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
      queryClient.invalidateQueries({ queryKey: ["seasons"] });
    });
    return () => disconnectRealtime();
  }, [connectRealtime, disconnectRealtime, isAuthenticated, queryClient]);

  return <AppRoutes />;
}
