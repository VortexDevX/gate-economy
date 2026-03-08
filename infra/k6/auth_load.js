import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");
const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    auth_storm: {
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
    http_req_duration: ["p(99)<500"],
    errors: ["rate<0.1"],
  },
};

export default function () {
  const id = `${__VU}_${__ITER}_${Date.now()}`;
  const username = `k6user_${id}`;
  const email = `k6_${id}@load.test`;
  const password = "LoadTest123!";

  // Register
  const regRes = http.post(
    `${BASE}/auth/register`,
    JSON.stringify({ username, email, password }),
    { headers: { "Content-Type": "application/json" } },
  );
  const regOk = check(regRes, {
    "register 201": (r) => r.status === 201,
  });
  errorRate.add(!regOk);

  if (!regOk) return;

  // Login
  const loginRes = http.post(
    `${BASE}/auth/login`,
    JSON.stringify({ email, password }),
    { headers: { "Content-Type": "application/json" } },
  );
  const loginOk = check(loginRes, {
    "login 200": (r) => r.status === 200,
    "has access_token": (r) => !!r.json("access_token"),
  });
  errorRate.add(!loginOk);

  sleep(0.1);
}
