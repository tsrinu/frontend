# Security audit — what's now protected (98 of 98 tests pass)

## TL;DR

| Category | Before | After |
|---|---|---|
| **Unauthenticated revenue endpoints** | 6 in billing | **0** — all require Bearer JWT |
| **Anonymous state-changing endpoints** | 24 across 5 APIs | **0** — all require Bearer JWT |
| **Security response headers** | 0 APIs sent them | **7** — every API sends 5 headers + X-Request-Id |
| **Request size limit** | None (DoS risk) | **1 MB default**, env-configurable |
| **Production-mode guard** | None — `DEV_MODE=true` could ship | **Refuses to boot** if `DEV_MODE=true` + `APP_ENV=production` |
| **/docs in production** | Always exposed | **Hidden** when `APP_ENV=production` |
| **Test count** | 60 | **98** (38 new security tests) |

---

## What I added this round

### 1. `shared/security.py` — reusable middleware (167 lines)

One file, three exports each API imports:

```python
from security import install_security, require_auth, verify_jwt
install_security(app)   # adds middleware + prod-guard + maybe hides /docs

@app.post("/protected")
def handler(claims: dict = Depends(require_auth)):
    user_id = claims["sub"]
```

What `install_security(app)` does on every API:

| Middleware | Purpose |
|---|---|
| **SecurityHeadersMiddleware** | Adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(),camera=(),microphone=()`, `Strict-Transport-Security` (HTTPS only), `X-Request-Id`. Strips `Server` header. |
| **RequestSizeLimitMiddleware** | Rejects requests with `Content-Length > MAX_BODY_BYTES` (default 1 MB) with HTTP 413. Prevents memory exhaustion. |
| **production_guard()** | Raises `RuntimeError` at startup if `DEV_MODE=true` AND `APP_ENV in (production, prod, live)`. Loud failure beats silent _devCode leaks. |
| **/docs hiding** | Sets `app.docs_url = None` in production. No more exposing Swagger UI to the public. |

### 2. JWT auth required on every state-changing endpoint

Before this round, anyone on the internet could call:
- `POST /billing/super-chat` — fake tip from any handle
- `POST /billing/memberships/subscribe` — create fake subscription records
- `POST /billing/gift-subs` — drain real subscriptions to fake accounts
- `POST /social/follow/{id}` — inflate follower counts
- `POST /social/comments/{id}` — spam comments
- `POST /social/watch-party` — create unlimited rooms
- `POST /notifications/preferences` — change other users' settings
- `POST /analytics/events` — pollute everyone's metrics

**After:** every one of those now returns **401 unauthorized** without a valid Bearer JWT. Confirmed by `test_*_requires_auth` tests in each API.

### 3. Public-by-design endpoints stayed public

These are intentionally NOT auth-gated (anyone should be able to read):
- `GET /healthz`, `GET /metrics` — for monitoring
- `GET /billing/memberships/tiers/{channelId}` — pricing page needs it
- `GET /billing/pricing/regional` — pricing page needs it
- `GET /live/streams/{id}` — viewer count, live indicator
- `GET /social/comments/{id}` — comments display below videos
- `GET /analytics/events/recent`, `GET /analytics/watch-time/today` — dashboard

---

## Endpoint protection matrix

| API | Endpoint | Auth | Why |
|---|---|---|---|
| auth-api | `POST /auth/email/start` | ❌ Public + rate-limited | Sign-in entry |
| auth-api | `POST /auth/email/verify` | ❌ Public + attempt-limited | Sign-in completion |
| auth-api | `POST /auth/sso/{provider}` | ❌ Public, **provider id_token validated** | SSO sign-in |
| auth-api | `POST /auth/passkey/register/*` | ✅ Bearer required | Logged-in user enrolls a passkey |
| auth-api | `POST /auth/passkey/login/*` | ❌ Public, **WebAuthn signature verified** | Sign-in via passkey |
| auth-api | `GET /auth/security/health` | ✅ Bearer required | Per-user score |
| auth-api | `POST /auth/2fa/*` | ✅ Bearer required | Enroll/verify 2FA |
| user-api | All `/users/me/*` | ✅ Bearer required | User-scoped resources |
| billing-api | `GET /memberships/tiers/{ch}` | ❌ Public | Pricing page |
| billing-api | `POST /memberships/subscribe` | ✅ **NEW** | Creates real subscription |
| billing-api | `POST /super-chat` | ✅ **NEW** | Pays money — must know who |
| billing-api | `POST /gift-subs` | ✅ **NEW** | Spends money |
| billing-api | `GET /creator/earnings` | ✅ **NEW** | Creator-private |
| billing-api | `GET /pricing/regional` | ❌ Public | Pricing page |
| live-api | `GET /streams/{id}` | ❌ Public | Live viewer count |
| live-api | `POST /streams/{id}/poll` | ✅ **NEW** | Streamer-only action |
| live-api | `POST .../vote` | ✅ **NEW** | Per-user vote tracking |
| live-api | `POST .../prediction` | ✅ **NEW** | Streamer-only |
| social-api | `GET /comments/{vid}` | ❌ Public | Read |
| social-api | `POST /comments/{vid}` | ✅ **NEW** | Write |
| social-api | `POST/DELETE /follow/{ch}` | ✅ **NEW** | Per-user state |
| social-api | `POST /watch-party*` | ✅ **NEW** | Room ownership |
| notification-api | `GET /inbox` | ✅ **NEW** | Per-user inbox |
| notification-api | `GET/PUT /preferences` | ✅ **NEW** | Per-user prefs |
| analytics-api | `POST /events` | ✅ **NEW** | Stops metric pollution |
| analytics-api | `GET /events/recent` | ❌ Public | Dashboard |

---

## Response headers — what every API now sets

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
X-Request-Id: <uuid or echoed from request>
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload   (HTTPS only)
```

Combined with the Caddyfile CSP at the edge, this covers OWASP's response-header recommendations.

---

## Test coverage breakdown (98 of 98 ✅)

| API | Functional tests | Security tests | Total |
|---|---:|---:|---:|
| auth-api | 17 | 3 (no devCode, request-id, headers) | 20 |
| user-api | 11 | 1 (headers) | 12 |
| billing-api | 11 | 8 (4 auth-required + 1 public stays + 3 headers) | 19 |
| live-api | 5 | 7 (3 auth-required + 1 public stays + 3 headers) | 12 |
| social-api | 5 | 8 (4 auth-required + 1 public stays + 3 headers) | 13 |
| notification-api | 4 | 6 (3 auth-required + 3 headers) | 10 |
| analytics-api | 7 | 5 (1 auth-required + 1 public stays + 3 headers) | 12 |
| **TOTAL** | **60** | **38** | **98** |

Run yourself:
```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API
test-all-apis.bat
```

---

## What's still NOT done (separate work)

Listed roughly in order of urgency for production:

| Sev | Item | Why deferred | ETA |
|---|---|---|---|
| 🟠 | Postgres for the 6 in-memory APIs | Different file change pattern per service, takes hours | 1-2 days |
| 🟠 | Redis rate-limit (cross-replica) | Needs Redis broker; only matters if you scale past 1 replica | 1 hour |
| 🟠 | Real email delivery (SendGrid) | Need a SendGrid account + API key | 30 min once configured |
| 🟡 | Cloudflare Turnstile CAPTCHA on `/auth/email/start` | Need Cloudflare account; CAPTCHA only matters once bots show up | 1 hour |
| 🟡 | starlette 1.0.1 (last CVE) | Needs fastapi 0.123+ released | 5 min once available |
| 🟡 | OpenTelemetry tracing | Sentry already gives errors + perf; OTel adds cross-service traces | 2 hours |

All documented in `FIX_PLAN.md` with copy-paste commands.

---

## Production deploy go/no-go

Before you flip `APP_ENV=production`:

| Check | How to verify | Status if config is right |
|---|---|---|
| ✅ DEV_MODE off | `curl /auth/email/start; grep -v devCode` | response has NO devCode |
| ✅ ALLOWED_ORIGINS = your domain | `curl -I -H "Origin: https://evil.com" /healthz; grep -v Access-Control-Allow-Origin` | header NOT present for evil.com |
| ✅ TLS terminated | `curl -vI https://api.distrebute.com/healthz` | `Let's Encrypt` cert |
| ✅ JWT keys shared across replicas | restart auth-api; token from before still verifies | introspect returns active=True |
| ✅ Security headers | `curl -I /healthz` | all 5 headers present + Strict-Transport-Security on HTTPS |
| ✅ Production guard works | start service with DEV_MODE=true APP_ENV=production | RuntimeError, refuses to boot |
| ✅ Request size limit | `curl -X POST /any --data "$(python -c "print('x'*2000000)")"` | 413 |
| ✅ 401 on protected endpoints | `curl -X POST /billing/super-chat -d '{}'` | 401 |

Hit all 8 and you can flip the switch.
