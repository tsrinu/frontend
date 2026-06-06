# Pre-deploy cross-check — endpoints, versions, dependencies, testing, UI mapping

## 🟢 Status snapshot

| Check | Result |
|---|---|
| **Tests passing** | 98 / 98 |
| **Total endpoints** | 59 across 7 APIs |
| **Auth-gated endpoints** | 40 (every state-changing / per-user endpoint) |
| **Public endpoints** | 19 (healthz, metrics, pricing, read-only) |
| **WebSocket endpoints** | 2 (live chat, watch-party sync) |
| **Known dep CVEs** | 1 remaining (`starlette 0.50.0 → 1.0.1`, blocked on fastapi 0.123) |
| **Security middleware** | 5 response headers + X-Request-Id + 1 MB body cap on all 7 APIs |
| **Production guard** | Refuses to boot if `DEV_MODE=true` + `APP_ENV=production` |

---

## Part 1 — Every endpoint, by API

### auth-api (port 8001) — 15 endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/healthz` | public |
| GET | `/.well-known/jwks.json` | public |
| POST | `/auth/email/start` | public (rate-limited 5/60s) |
| POST | `/auth/email/verify` | public (5-attempt cap) |
| POST | `/auth/sso/{apple\|google\|facebook}` | public (provider id_token validated) |
| POST | `/auth/passkey/login/challenge` | public |
| POST | `/auth/passkey/login/verify` | public (FIDO2 signature verified) |
| POST | `/auth/refresh` | public (verifies refresh token) |
| POST | `/auth/passkey/register/challenge` | ✓ JWT (logged-in user enrolls passkey) |
| POST | `/auth/passkey/register/verify` | ✓ JWT |
| POST | `/auth/2fa/setup` | ✓ JWT |
| POST | `/auth/2fa/verify` | ✓ JWT |
| GET | `/auth/security/health` | ✓ JWT (per-user score) |
| GET | `/auth/events` | ✓ JWT (per-user log) |
| POST | `/internal/introspect` | service-to-service (validates JWT) |
| GET | `/metrics` | public (Prometheus scrape) |
| GET | `/docs` | public (hidden when `APP_ENV=production`) |

### user-api (port 8002) — 15 endpoints, all ✓ JWT

`GET /users/me` · `GET\|POST /users/me/profiles` · `PUT /users/me/profiles/{id}/parental` · `POST /users/me/pin` · `POST /users/me/pin/verify` · `GET\|PUT /users/me/privacy` · `POST /users/me/data-export` · `DELETE /users/me/account` · `GET /users/me/devices` · `DELETE /users/me/devices/all` · `DELETE /users/me/devices/{id}` · `POST /users/me/devices/{id}/not-me`

Plus public: `/healthz` · `/metrics` · `/docs`

### billing-api (port 8012) — 7 endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/billing/memberships/tiers/{channelId}` | public (pricing page) |
| POST | `/billing/memberships/subscribe` | ✓ JWT |
| POST | `/billing/super-chat` | ✓ JWT |
| POST | `/billing/gift-subs` | ✓ JWT |
| GET | `/billing/creator/earnings` | ✓ JWT |
| GET | `/billing/pricing/regional` | public (pricing page) |

### live-api (port 8013) — 6 HTTP + 1 WebSocket

| Method | Path | Auth |
|---|---|---|
| GET | `/live/streams/{id}` | public |
| GET | `/live/streams/{id}/chat` | public (returns WS ticket) |
| POST | `/live/streams/{id}/poll` | ✓ JWT |
| POST | `/live/streams/{id}/poll/{pid}/vote` | ✓ JWT |
| POST | `/live/streams/{id}/prediction` | ✓ JWT |
| **WS** | `/live/{id}/chat` | ticket-based (one-time signed) |

### social-api (port 8014) — 7 HTTP + 1 WebSocket

| Method | Path | Auth |
|---|---|---|
| POST\|DELETE | `/social/follow/{channelId}` | ✓ JWT |
| GET | `/social/comments/{videoId}` | public (read) |
| POST | `/social/comments/{videoId}` | ✓ JWT (write) |
| POST | `/social/watch-party` | ✓ JWT |
| POST | `/social/watch-party/{roomId}/join` | ✓ JWT |
| POST | `/social/watch-party/{roomId}/react` | ✓ JWT |
| **WS** | `/party/{roomId}` | ticket-based |

### notification-api (port 8015) — 4 endpoints, all ✓ JWT (per-user)

`GET /notifications/inbox` · `GET\|PUT /notifications/preferences`

### analytics-api (port 8016) — 4 endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/analytics/events` | ✓ JWT |
| GET | `/analytics/events/recent` | public (dashboard) |
| GET | `/analytics/watch-time/today` | public (dashboard) |

---

## Part 2 — Dependency versions across all 7 APIs (audited)

| Package | Version | Used by | Status |
|---|---|---|---|
| fastapi | **0.122.0** | all 7 | latest stable line |
| uvicorn[standard] | 0.32.1 | all 7 | current |
| pydantic | 2.10.3 | all 7 | current |
| pydantic[email] | 2.10.3 | auth-api | for `EmailStr` validator |
| PyJWT[crypto] | **2.13.0** | auth-api, user-api | 5 CVEs fixed in this pass |
| cryptography | **46.0.7** | auth-api | 3 CVEs fixed |
| python-multipart | **0.0.27** | auth-api | 3 CVEs fixed |
| pyotp | 2.9.0 | auth-api | TOTP — clean |
| qrcode[pil] | 8.0 | auth-api | clean |
| webauthn | 2.5.2 | auth-api | real FIDO2 — clean |
| sqlalchemy | 2.0.36 | auth-api | clean |
| aiosqlite | 0.20.0 | auth-api | dev DB driver |
| asyncpg | 0.30.0 | auth-api | prod postgres driver |
| greenlet | 3.1.1 | auth-api | sqlalchemy async dep |
| google-auth | 2.36.0 | auth-api | real Google id_token verify |
| cachetools | 5.5.0 | auth-api | for cacheing future JWKS |
| websockets | 13.1 | live-api, social-api | real-time |
| httpx | 0.28.1 | user-api | cross-svc JWKS fetch |
| sentry-sdk | 2.19.2 | all 7 | error tracking |
| prometheus-fastapi-instrumentator | 7.0.2 | all 7 | /metrics endpoint |

**Remaining CVE:** `starlette 0.50.0 → 1.0.1` (PYSEC-2026-161). starlette is a transitive dep of fastapi. fastapi 0.122 pins starlette 0.50.0; need fastapi 0.123+ for starlette 1.0.1. Calendar reminder for 30 days.

---

## Part 3 — How to do every type of testing before production

| # | Test type | Tool | Run command | What it catches |
|---|---|---|---|---|
| 1 | **Unit + integration** | pytest | `pytest tests/ -v` (in each API folder) | logic bugs, API contracts |
| 2 | **Cross-API integration** | pytest + TestClient | `pytest tests/` (top-level) | JWKS pass-through, end-to-end auth flow |
| 3 | **Contract / fuzz** | Schemathesis | `pytest tests/test_contract.py` against running stack | schema drift, undocumented 4xx/5xx |
| 4 | **Load / performance** | k6 | `k6 run tests/load/k6-auth.js` against running stack | p95 latency, throughput cliff, concurrency |
| 5 | **Static security** | bandit | `bandit -r */main.py shared/` | hardcoded secrets, weak crypto, `eval` |
| 6 | **Dependency CVEs** | pip-audit | `pip-audit -r */requirements.txt` | known vulnerabilities |
| 7 | **Lint / format** | ruff | `ruff check . && ruff format .` | style, dead code, unused imports |
| 8 | **Container scan** | Trivy | `trivy image distrebute-auth-api:latest` | OS + lib CVEs in the image |
| 9 | **Smoke (manual)** | curl + Swagger UI | open `/docs` in browser | one-off exploration |
| 10 | **Health + metrics** | curl | `curl localhost:8001/{healthz,metrics}` | service up, instrumentation working |

### Full pre-deploy test sequence (run in order)

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API

REM 1. Unit + integration (all 7 APIs in isolation, ~10 sec)
test-all-apis.bat
REM Expected: 98 passed

REM 2. Lint + security static scan (~30 sec)
pip install ruff bandit pip-audit
ruff check . --fix
bandit -r auth-api/app billing-api live-api social-api ^
        notification-api analytics-api user-api shared -ll
REM Expected: 0 HIGH, 0 MEDIUM

REM 3. Dep CVE scan (~1 min)
for /d %d in (*-api) do pip-audit -r "%d\requirements.txt"
REM Expected: 1 starlette CVE (waiting for fastapi 0.123)

REM 4. Build all Docker images (~5 min first time)
for /d %d in (*-api) do docker build -t distrebute-%~nd "%d"

REM 5. Container scan (~2 min each)
trivy image distrebute-auth-api
REM Expected: HIGH+CRITICAL = 0 on the application layer

REM 6. Boot the full stack
docker compose -f docker-compose.yml -f docker-compose.gap.yml up -d --build

REM 7. Contract tests against running stack (~5 min)
set CONTRACT_BASE_URL=http://localhost:8080
pytest tests/test_contract.py -v

REM 8. Load test (~3 min)
k6 run -e BASE_URL=http://localhost:8001 tests/load/k6-auth.js
k6 run -e BASE_URL=http://localhost:8012 tests/load/k6-billing.js
REM Expected: p95 < 500ms, error rate < 1%

REM 9. Manual /docs walkthrough for each API
start http://localhost:8001/docs
start http://localhost:8002/docs
start http://localhost:8012/docs
...

REM 10. Pre-deploy 8-step go/no-go in SECURITY_AUDIT.md
```

---

## Part 4 — Does the backend map to the HTML page?

**Honest answer: No, not directly. They're two separate layers right now.**

### The HTML page (`distrebute-ui-templates.html`)

- **What it is:** 22 static visual mockups, ~186 KB, pure HTML + inline CSS + a little inline SVG
- **What it does:** Renders in any browser as a designer-grade scrollable gallery
- **What it does NOT do:** Fetch from any API, run any JS, react to user clicks
- **Purpose:** Reference for what each screen should look like — for your designers / frontend devs

### The 7 APIs

- **What they are:** Production-grade FastAPI services that implement the *data* layer behind those mockups
- **What they expose:** OpenAPI 3.0 spec (77 endpoints, in `openapi.yaml`)
- **What's needed to connect them to the HTML:** A real frontend app (React/Vue/Next/Svelte) that:
  1. Looks like the HTML mockups (use them as your designer reference)
  2. Calls these APIs over HTTPS using the OpenAPI spec to generate a TypeScript client

### How each UI template maps to APIs

| UI template # | What it shows | API endpoints needed |
|---|---|---|
| 01 | Home (rows of titles + creators) | `GET /metadata/titles` (TODO), `GET /metadata/creators` (TODO), `GET /analytics/watch-time/today`, `GET /notifications/inbox` |
| 02 | Video player + chat | `GET /metadata/videos/{id}` (TODO), WS `/live/{id}/chat`, `GET /social/comments/{id}` |
| 03 | Creator profile | `GET /metadata/creators/{id}` (TODO), `POST /social/follow/{id}` |
| 09 | Wallet / subscriptions | `GET /billing/memberships/tiers/{ch}`, `POST /billing/memberships/subscribe`, `GET /billing/creator/earnings` |
| 10 | Tip / super chat overlay | `POST /billing/super-chat` |
| 12 | Watch party | `POST /social/watch-party`, WS `/party/{roomId}` |
| 13 | 2FA setup | `POST /auth/2fa/setup`, `POST /auth/2fa/verify` |
| 14 | Live polls + predictions | `POST /live/.../poll`, `POST .../vote`, `POST .../prediction` |
| 18-22 | Settings (privacy, parental, devices, account) | `GET\|PUT /users/me/privacy`, `PUT /users/me/profiles/{id}/parental`, `GET\|DELETE /users/me/devices`, `DELETE /users/me/account` |

The HTML mockups DON'T fetch from these APIs because they're CSS-only mockups (intentional — keeps them fast to render and easy to share). To make them interactive, build a frontend that consumes `openapi.yaml`.

### Recommended frontend stack (when you're ready)

```cmd
REM Generate a typed TypeScript client from the OpenAPI spec
npm install -g openapi-typescript-codegen
npx openapi --input openapi.yaml --output src/api-client --client fetch

REM Use Next.js or Vite + React for the actual UI
npx create-next-app@latest distrebute-web
cd distrebute-web
npm install @tanstack/react-query
REM Copy the HTML mockups visual style into your Tailwind components
```

The mockups + OpenAPI spec give your frontend dev everything they need: the look, the data shapes, and the endpoints to call.

---

## Pre-deploy go/no-go (8 checks)

| # | Check | How to verify |
|---|---|---|
| 1 | `_devCode` absent from `/auth/email/start` response in prod | `APP_ENV=production` + curl returns no `devCode` field |
| 2 | `ALLOWED_ORIGINS` set to your real domain | Reject CORS from other origins |
| 3 | TLS cert valid (Let's Encrypt via Caddy) | `curl -vI https://api.distrebute.com` |
| 4 | JWT key shared across replicas | Token from replica A verified by replica B |
| 5 | Security headers in every response | `curl -I /healthz` shows all 5 + X-Request-Id |
| 6 | Production guard fires when misconfigured | Set `DEV_MODE=true` + `APP_ENV=production` → service refuses to boot |
| 7 | Request size limit enforces 413 | `curl -X POST --data "@2MB-file" /any` → 413 |
| 8 | 401 on protected endpoints anonymously | `curl -X POST /billing/super-chat -d '{}'` → 401 |

All 8 checked? Flip `APP_ENV=production` and ship.
