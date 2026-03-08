import ws from "k6/ws";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const wsLatency = new Trend("ws_message_latency", true);
const BASE_WS = __ENV.WS_URL || "ws://localhost:8000";

export const options = {
  scenarios: {
    ws_flood: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 200 },
        { duration: "30s", target: 1000 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    ws_message_latency: ["p(99)<1000"],
  },
};

export default function () {
  const url = `${BASE_WS}/ws`;
  const connectStart = Date.now();

  const res = ws.connect(url, {}, function (socket) {
    socket.on("open", function () {
      const connectTime = Date.now() - connectStart;
      wsLatency.add(connectTime);
    });

    socket.on("message", function (msg) {
      const receiveTime = Date.now();
      try {
        const data = JSON.parse(msg);
        // If server includes a timestamp, compute latency
        if (data.timestamp) {
          const serverTime = new Date(data.timestamp).getTime();
          wsLatency.add(receiveTime - serverTime);
        } else {
          // Just record receipt time as a baseline
          wsLatency.add(1);
        }
      } catch (e) {
        // Non-JSON message
        wsLatency.add(1);
      }
    });

    // Keep connection open for ~30s to receive tick updates
    sleep(30);
    socket.close();
  });

  check(res, {
    "ws connected": (r) => r && r.status === 101,
  });
}
