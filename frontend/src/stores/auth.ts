import { create } from "zustand";
import { login as apiLogin, getMe } from "../api/auth";
import { setTokens, clearTokens, getAccessToken } from "../api/client";
import type { PlayerResponse } from "../api/types";

interface AuthState {
  player: PlayerResponse | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  bootstrap: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  player: null,
  isAuthenticated: false,
  isBootstrapping: true,

  login: async (email: string, password: string) => {
    const tokens = await apiLogin({ email, password });
    setTokens(tokens.access_token, tokens.refresh_token);
    const player = await getMe();
    set({ player, isAuthenticated: true });
  },

  logout: () => {
    clearTokens();
    set({ player: null, isAuthenticated: false });
  },

  bootstrap: async () => {
    const token = getAccessToken();
    if (!token) {
      set({ isBootstrapping: false });
      return;
    }
    try {
      const player = await getMe();
      set({ player, isAuthenticated: true, isBootstrapping: false });
    } catch {
      clearTokens();
      set({ isBootstrapping: false });
    }
  },
}));
