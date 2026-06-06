# social-api

**Port:** `8014` · **Module:** `main:app`

Comments, follows, watch parties, WebSocket reactions

## Run locally

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\social-api
python -m pip install -r requirements.txt

set DEV_MODE=true
python -m uvicorn main:app --host 127.0.0.1 --port 8014
```

Then open: **http://127.0.0.1:8014/docs** — interactive Swagger UI.

## Run in Docker

```cmd
docker build -t distrebute-social-api .
docker run -p 8014:8014 -e DEV_MODE=true distrebute-social-api
```

## Run tests for this API only

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\social-api
python -m pip install -r ../tests/requirements.txt
pytest tests/ -v
```

## Endpoints exposed

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{status: "ok", service: "social-api"}` |
| GET | `/metrics` | Prometheus text format (scrape from Grafana) |
| GET | `/docs` | Swagger UI (interactive) |
| GET | `/openapi.json` | OpenAPI 3.0 spec |

Plus the business endpoints — see `openapi.json` after the API is running, or the master spec at `../openapi.yaml`.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `PORT` | 8014 | Override only if your reverse proxy needs a different port |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Comma-separated for CORS |
| `DEV_MODE` | `true` | **MUST be `false` in production** |
| `LOG_LEVEL` | `info` | debug / info / warning / error |
| `SENTRY_DSN` | (unset) | Set to enable Sentry error tracking |
| `APP_VERSION` | `dev` | Tagged in Sentry releases |


