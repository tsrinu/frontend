// Load test for billing-service.
//   k6 run -e BASE_URL=http://localhost:8012 tests/load/k6-billing.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [{ duration: '30s', target: 20 }, { duration: '1m', target: 100 }, { duration: '30s', target: 0 }],
  thresholds: { http_req_duration: ['p(95)<300'], http_req_failed: ['rate<0.01'] },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8012';

export default function () {
  check(http.get(`${BASE}/billing/memberships/tiers/ch_demo`), { 'tiers 200': r => r.status === 200 });
  check(http.get(`${BASE}/billing/creator/earnings?range=30d`), { 'earnings 200': r => r.status === 200 });
  check(http.get(`${BASE}/billing/pricing/regional?region=IN`), { 'pricing INR': r => r.status === 200 });
  sleep(0.5);
}
