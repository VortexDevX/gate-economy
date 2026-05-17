import { create } from "zustand";

type ThemeMode = "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
  bootstrap: () => void;
}

const THEME_KEY = "dge_theme_mode";

function applyTheme(mode: ThemeMode) {
  const root = document.documentElement;
  if (mode === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: "light",

  setMode: (mode) => {
    localStorage.setItem(THEME_KEY, mode);
    applyTheme(mode);
    set({ mode });
  },

  toggleMode: () => {
    const next = get().mode === "light" ? "dark" : "light";
    get().setMode(next);
  },

  bootstrap: () => {
    const stored = localStorage.getItem(THEME_KEY) as ThemeMode | null;
    const prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    const mode: ThemeMode = stored ?? (prefersDark ? "dark" : "light");
    applyTheme(mode);
    set({ mode });
  },
}));
