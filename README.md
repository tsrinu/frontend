# distrebute APIs — 7 microservices + live demo cockpit

## What's here

```
API/
├── distrebute-ui-templates.html         ← 22-template visual mockup gallery (static, designer reference)
├── demo.html                            ← ★ LIVE COCKPIT — wires the mockups to the running APIs
├── README.md                            ← this file
├── PRE_DEPLOY_CHECKLIST.md              ← every endpoint + every version + 8-step go/no-go
├── SECURITY_AUDIT.md                    ← 98/98 tests + security middleware + auth audit
├── TESTING_TYPES.md                     ← 20 testing approaches with commands
├── FIX_PLAN.md                          ← remaining issues, ETA per fix
│
├── run-all-apis.bat                     ← double-click → boots all 7 APIs in separate windows
├── test-all-apis.bat                    ← double-click → runs all 98 tests
│
├── auth-api/                port 8001   ✓ real WebAuthn, JWT (RS256), 2FA, SSO, SQLAlchemy
├── user-api/                port 8002   ✓ profiles, devices, scrypt PIN
├── billing-api/             port 8012   ✓ memberships, super-chats, regional pricing
├── live-api/                port 8013   ✓ streams, polls, predictions + WebSocket chat
├── social-api/              port 8014   ✓ comments, watch parties + WebSocket
├── notification-api/        port 8015   ✓ inbox, preferences
├── analytics-api/           port 8016   ✓ event firehose
│
├── shared/
│   ├── observability.py                Sentry + Prometheus bootstrap
│   └── security.py                     Security headers + JWT verify + prod guard
├── tests/                              cross-API contract + load tests
├── infra/digitalocean/                 production deploy infra
└── .github/workflows/ci.yml            CI pipeline
```

## To see it all work end-to-end (5 minutes)

```cmd
REM 1. Boot all 7 APIs (opens 7 cmd windows)
double-click run-all-apis.bat

REM 2. Wait 5 seconds for them to start

REM 3. Open demo.html in your browser
double-click demo.html

REM 4. Sign in with your email (OTP shown in DEV_MODE)

REM 5. Click ▶ Run flow on any card — see the real HTTP requests + responses
```

## Live demo cockpit (`demo.html`)

The 22 mockups in `distrebute-ui-templates.html` are visual designs only — pure HTML+CSS.
`demo.html` is **the bridge that wires them to your live backend**:

- 7 status pills at the top, one per API — green when reachable, red when down
- Sign-in panel (email OTP — code is shown in DEV_MODE so you don't need real email)
- **15 flow cards**, each runs the API sequence for one UI template
- Modal output shows every HTTP request + response with status codes, request bodies, parsed JSON

What you can actually test end-to-end:
- Auth: sign in, security health score, recent events
- Privacy: read + toggle data controls
- Devices: list, sign-out-all, re-list
- Parental PIN: set with scrypt hash, verify (correct + wrong)
- 2FA: generate QR code (rendered inline), verify TOTP
- Wallet: 12-month earnings trend
- Memberships: list 4 tiers, subscribe
- Super chats: $5/$25/$100 (blue/pink/gold colors)
- Live polls: create, vote
- Watch party: create room with invite URL
- Follow + comments
- Inbox notifications
- Analytics: emit event + read dashboard
- Live stream metadata + WebSocket ticket
- Regional pricing: INR / USD / EUR / JPY / BRL

## How to test before production

| Test type | Command (in this folder) |
|---|---|
| Unit + integration (all 7 APIs) | `test-all-apis.bat` → 98 pass |
| Manual via cockpit | open `demo.html` → click flows |
| Manual via Swagger UI | http://localhost:8001/docs (and 8002…8016) |
| Load | `k6 run -e BASE_URL=http://localhost:8001 tests\load\k6-auth.js` |
| Dep CVEs | `pip-audit -r */requirements.txt` |
| Security scan | `bandit -r */main.py shared/ -ll` |
| Lint | `ruff check . --fix` |

Full pre-deploy 8-step go/no-go in **`PRE_DEPLOY_CHECKLIST.md`**.

## Per-API endpoints

Open each API's `/docs` URL while it's running for the full interactive spec:

| API | Port | docs | What it owns |
|---|---|---|---|
| auth | 8001 | http://localhost:8001/docs | sign-in, JWT, passkey, 2FA, SSO |
| user | 8002 | http://localhost:8002/docs | profiles, devices, PIN, privacy |
| billing | 8012 | http://localhost:8012/docs | memberships, super-chats, pricing |
| live | 8013 | http://localhost:8013/docs | streams, polls, predictions |
| social | 8014 | http://localhost:8014/docs | comments, follows, watch parties |
| notification | 8015 | http://localhost:8015/docs | inbox, preferences |
| analytics | 8016 | http://localhost:8016/docs | event firehose, watch-time |

## Production deploy

`infra/digitalocean/` has provision.sh + Caddyfile (TLS) + .env.production template + deploy.sh.
Run `provision.sh` on a fresh Ubuntu 24.04 droplet → you're live in ~90 minutes.
