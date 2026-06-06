# auth-api

**Port:** `8001` · **Module:** `app.main:app`

Sign-in, JWT (RS256), passkey (WebAuthn), 2FA (TOTP), rate limiting, SSO

## Run locally

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\auth-api
python -m pip install -r requirements.txt
set JWT_KEY_DIR=%TEMP%\\jwt-keys
set DEV_MODE=true
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Then open: **http://127.0.0.1:8001/docs** — interactive Swagger UI.

## Run in Docker

```cmd
docker build -t distrebute-auth-api .
docker run -p 8001:8001 -e DEV_MODE=true distrebute-auth-api
```

## Run tests for this API only

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\auth-api
python -m pip install -r ../tests/requirements.txt
pytest tests/ -v
```

## Endpoints exposed

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{status: "ok", service: "auth-api"}` |
| GET | `/metrics` | Prometheus text format (scrape from Grafana) |
| GET | `/docs` | Swagger UI (interactive) |
| GET | `/openapi.json` | OpenAPI 3.0 spec |

Plus the business endpoints — see `openapi.json` after the API is running, or the master spec at `../openapi.yaml`.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `PORT` | 8001 | Override only if your reverse proxy needs a different port |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Comma-separated for CORS |
| `DEV_MODE` | `true` | **MUST be `false` in production** |
| `LOG_LEVEL` | `info` | debug / info / warning / error |
| `SENTRY_DSN` | (unset) | Set to enable Sentry error tracking |
| `APP_VERSION` | `dev` | Tagged in Sentry releases |

## Auth-API specific vars

| Var | Default | Notes |
|---|---|---|
| `JWT_KEY_DIR` | `/app/keys` | Where the RSA keypair lives — generated on first boot if missing |
| `JWT_ISSUER` | `https://distrebute.com` | iss claim in tokens |
| `ACCESS_TTL_SECONDS` | `900` | 15 min access token |
| `REFRESH_TTL_SECONDS` | `2592000` | 30 day refresh token |
| `DATABASE_URL` | `sqlite+aiosqlite:///./auth.db` | Switch to `postgresql+asyncpg://...` in prod |
| `WEBAUTHN_RP_ID` | `localhost` | Must match your domain in prod |
| `WEBAUTHN_RP_ORIGIN` | `http://localhost:8080` | Must match your origin in prod |
| `GOOGLE_CLIENT_ID` | (unset) | Real Google OAuth2 client ID |
| `APPLE_CLIENT_ID` | (unset) | Apple Services ID |
| `FACEBOOK_APP_ID` | (unset) | Facebook App ID |
| `FACEBOOK_APP_SECRET` | (unset) | Facebook App secret |

