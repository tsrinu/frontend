// k6 load test for auth-service. Run with:
//   k6 run -e BASE_URL=http://localhost:8001 tests/load/k6-auth.js
//
// Defaults: ramps to 50 virtual users over 1 minute, holds for 2 min, ramps down.
// Reports p95 latency, error rate, requests/sec.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://localhost:8001';

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // ramp up
    { duration: '1m',  target: 50 },   // steady
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests <500ms
    errors: ['rate<0.01'],             // <1% errors
  },
};

export default function () {
  // healthz baseline
  let r = http.get(`${BASE}/healthz`);
  check(r, { 'healthz 200': (res) => res.status === 200 }) || errorRate.add(1);

  // JWKS — heaviest read
  r = http.get(`${BASE}/.well-known/jwks.json`);
  check(r, { 'jwks 200': (res) => res.status === 200 }) || errorRate.add(1);

  // Sign-in flow (rate-limited at 5/60s, so most will 429 — that's OK,
  // we're testing the limiter's overhead + behavior under load)
  const email = `vu${__VU}@loadtest.com`;
  r = http.post(`${BASE}/auth/email/start`,
                JSON.stringify({ email }),
                { headers: { 'Content-Type': 'application/json' } });
  check(r, { 'start 202 or 429': (res) => [202, 429].includes(res.status) }) || errorRate.add(1);

  sleep(1);
}
