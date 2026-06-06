# analytics-api

**Port:** `8016` · **Module:** `main:app`

Event firehose (bounded), watch-time aggregates

## Run locally

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\analytics-api
python -m pip install -r requirements.txt

set DEV_MODE=true
python -m uvicorn main:app --host 127.0.0.1 --port 8016
```

Then open: **http://127.0.0.1:8016/docs** — interactive Swagger UI.

## Run in Docker

```cmd
docker build -t distrebute-analytics-api .
docker run -p 8016:8016 -e DEV_MODE=true distrebute-analytics-api
```

## Run tests for this API only

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\analytics-api
python -m pip install -r ../tests/requirements.txt
pytest tests/ -v
```

## Endpoints exposed

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{status: "ok", service: "analytics-api"}` |
| GET | `/metrics` | Prometheus text format (scrape from Grafana) |
| GET | `/docs` | Swagger UI (interactive) |
| GET | `/openapi.json` | OpenAPI 3.0 spec |

Plus the business endpoints — see `openapi.json` after the API is running, or the master spec at `../openapi.yaml`.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `PORT` | 8016 | Override only if your reverse proxy needs a different port |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Comma-separated for CORS |
| `DEV_MODE` | `true` | **MUST be `false` in production** |
| `LOG_LEVEL` | `info` | debug / info / warning / error |
| `SENTRY_DSN` | (unset) | Set to enable Sentry error tracking |
| `APP_VERSION` | `dev` | Tagged in Sentry releases |


