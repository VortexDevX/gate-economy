import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");
const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    order_storm: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 100 },
        { duration: "30s", target: 500 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(99)<500"],
    errors: ["rate<0.3"],
  },
};

// Setup: register a pool of users and return tokens
export function setup() {
  const tokens = [];
  for (let i = 0; i < 50; i++) {
    const id = `order_${i}_${Date.now()}`;
    const email = `order_${id}@load.test`;
    const password = "LoadTest123!";

    const regRes = http.post(
      `${BASE}/auth/register`,
      JSON.stringify({
        username: `orderer_${id}`,
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
  if (!data.tokens || data.tokens.length === 0) return;

  const token = data.tokens[__VU % data.tokens.length];
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // Discover gate intent
  const discoverRes = http.post(
    `${BASE}/intents`,
    JSON.stringify({
      intent_type: "DISCOVER_GATE",
      payload: {},
    }),
    { headers },
  );
  check(discoverRes, {
    "discover accepted": (r) => r.status === 201 || r.status === 200,
  });

  // Place buy order intent
  // Use a random gate_id placeholder — will be rejected if gate doesn't exist
  // This tests throughput, not correctness
  const orderRes = http.post(
    `${BASE}/intents`,
    JSON.stringify({
      intent_type: "PLACE_ORDER",
      payload: {
        asset_type: "GATE_SHARE",
        asset_id: "00000000-0000-0000-0000-000000000001",
        side: "BUY",
        quantity: 1,
        price_limit_micro: 100000,
      },
    }),
    { headers },
  );
  const orderOk = check(orderRes, {
    "order accepted": (r) => r.status === 201 || r.status === 200,
  });
  errorRate.add(!orderOk);

  sleep(5);
}
