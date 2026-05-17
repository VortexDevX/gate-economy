import { create } from "zustand";
import { getAccessToken } from "../api/client";

type ConnectionState = "idle" | "connecting" | "connected" | "reconnecting" | "disconnected";

interface TickUpdatePayload {
  type: string;
  tick_number?: number;
}

interface RealtimeState {
  connectionState: ConnectionState;
  lastTick: number | null;
  connect: (onTick: (tickNumber: number) => void) => void;
  disconnect: () => void;
}

let socket: WebSocket | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;
let isManualClose = false;

function clearRetryTimer() {
  if (retryTimer) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
}

function scheduleReconnect(connectFn: () => void) {
  clearRetryTimer();
  reconnectAttempts += 1;
  const delayMs = Math.min(1_000 * 2 ** Math.min(reconnectAttempts, 5), 20_000);
  retryTimer = setTimeout(connectFn, delayMs);
}

export const useRealtimeStore = create<RealtimeState>((set) => ({
  connectionState: "idle",
  lastTick: null,

  connect: (onTick) => {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      set({ connectionState: "disconnected" });
      return;
    }

    isManualClose = false;
    set({ connectionState: reconnectAttempts > 0 ? "reconnecting" : "connecting" });

    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${scheme}://${window.location.host}/ws/feed?token=${encodeURIComponent(token)}`;
    socket = new WebSocket(url);

    socket.onopen = () => {
      reconnectAttempts = 0;
      set({ connectionState: "connected" });
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as TickUpdatePayload;
        if (payload.type === "tick_update" && typeof payload.tick_number === "number") {
          set({ lastTick: payload.tick_number });
          onTick(payload.tick_number);
        }
      } catch {
        // Ignore non-JSON payloads
      }
    };

    socket.onerror = () => {
      // onclose handles reconnection
    };

    socket.onclose = () => {
      socket = null;
      if (isManualClose) {
        set({ connectionState: "disconnected" });
        return;
      }
      set({ connectionState: "reconnecting" });
      scheduleReconnect(() => useRealtimeStore.getState().connect(onTick));
    };
  },

  disconnect: () => {
    isManualClose = true;
    clearRetryTimer();
    reconnectAttempts = 0;
    if (socket) {
      socket.close();
      socket = null;
    }
    set({ connectionState: "disconnected" });
  },
}));
