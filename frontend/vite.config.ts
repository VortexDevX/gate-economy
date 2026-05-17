import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import type { IncomingMessage } from "http";

const API_TARGET = process.env.VITE_API_TARGET || "http://localhost:8000";

function bypassForHtml(req: IncomingMessage) {
  if (req.headers.accept && req.headers.accept.includes("text/html")) {
    return "/index.html";
  }
}

const proxyPaths = [
  "/auth",
  "/players",
  "/intents",
  "/simulation",
  "/gates",
  "/orders",
  "/market",
  "/guilds",
  "/news",
  "/events",
  "/leaderboard",
  "/seasons",
  "/admin",
  "/metrics",
  "/health",
  "/ready",
];

const proxyConfig: Record<string, object> = {};
for (const path of proxyPaths) {
  proxyConfig[path] = {
    target: API_TARGET,
    bypass: bypassForHtml,
  };
}
proxyConfig["/ws"] = {
  target: API_TARGET,
  ws: true,
  bypass: bypassForHtml,
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: proxyConfig,
  },
});
