import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");
const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    mixed: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 100 },
        { duration: "40s", target: 500 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(99)<500"],
    errors: ["rate<0.2"],
  },
};

export function setup() {
  const tokens = [];
  for (let i = 0; i < 30; i++) {
    const id = `mix_${i}_${Date.now()}`;
    const email = `mix_${id}@load.test`;
    const password = "LoadTest123!";

    const regRes = http.post(
      `${BASE}/auth/register`,
      JSON.stringify({
        username: `mixer_${id}`,
        email,
        password,
      }),
      { headers: { "Content-Type": "application/json" } },
    );

    if (regRes.status === 201) {
      const loginRes = http.post(
        `${BASE}/auth/login`,
        JSON.stringify({ email, password }),
        { headers: { "Content-Type": "application/json" } },
      );
      if (loginRes.status === 200) {
        tokens.push(loginRes.json("access_token"));
      }
    }
  }
  return { tokens };
}

export default function (data) {
  const roll = Math.random();
  const hasToken = data.tokens && data.tokens.length > 0;
  const token = hasToken ? data.tokens[__VU % data.tokens.length] : null;
  const authHeaders = token
    ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json" };

  if (roll < 0.6) {
    // ── 60% reads ──
    const readRoll = Math.random();

    if (readRoll < 0.25) {
      const r = http.get(`${BASE}/gates`);
      check(r, { "gates 200": (r) => r.status === 200 });
    } else if (readRoll < 0.5) {
      const r = http.get(`${BASE}/leaderboard`);
      check(r, { "leaderboard 200": (r) => r.status === 200 });
    } else if (readRoll < 0.75) {
      const r = http.get(`${BASE}/news`);
      check(r, { "news 200": (r) => r.status === 200 });
    } else {
      const r = http.get(`${BASE}/simulation/status`);
      check(r, { "sim status 200": (r) => r.status === 200 });
    }
  } else if (roll < 0.9 && hasToken) {
    // ── 30% orders ──
    const r = http.post(
      `${BASE}/intents`,
      JSON.stringify({
        intent_type: "PLACE_ORDER",
        payload: {
          asset_type: "GATE_SHARE",
          asset_id: "00000000-0000-0000-0000-000000000001",
          side: "BUY",
          quantity: 1,
          price_limit_micro: 50000,
        },
      }),
      { headers: authHeaders },
    );
    const ok = check(r, {
      "order intent accepted": (r) => r.status === 201 || r.status === 200,
    });
    errorRate.add(!ok);
  } else if (hasToken) {
    // ── 10% discovery ──
    const r = http.post(
      `${BASE}/intents`,
      JSON.stringify({
        intent_type: "DISCOVER_GATE",
        payload: {},
      }),
      { headers: authHeaders },
    );
    const ok = check(r, {
      "discover accepted": (r) => r.status === 201 || r.status === 200,
    });
    errorRate.add(!ok);
  }

  sleep(1 + Math.random() * 2);
}
