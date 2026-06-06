"""distrebute analytics-service (stub) — event firehose."""
import os
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

app = FastAPI(title="distrebute analytics-service", version="0.1.0")


# Observability — exposes /metrics, integrates Sentry if SENTRY_DSN set
try:
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.abspath(_o.path.join(_o.path.dirname(__file__), "..", "..", "shared")))
    _s.path.insert(0, _o.path.abspath(_o.path.join(_o.path.dirname(__file__), "..", "shared")))
    from observability import init_observability as _init_obs
    _init_obs(app, _o.path.basename(_o.path.dirname(_o.path.abspath(__file__))) or "service")
except Exception as _e:
    import logging as _log
    _log.getLogger().warning("observability skipped: %s", _e)


# ────────────────────────────────────────────────────────────────
# Shared security middleware (response headers, request size cap,
# request ID, production-mode guard, /docs hidden in prod)
# ────────────────────────────────────────────────────────────────
try:
    import sys as _ss, os as _so
    _ss.path.insert(0, _so.path.abspath(_so.path.join(_so.path.dirname(__file__), "..", "..", "shared")))
    _ss.path.insert(0, _so.path.abspath(_so.path.join(_so.path.dirname(__file__), "..", "shared")))
    from security import install_security as _install_sec, require_auth as _require_auth
    _install_sec(app)
except Exception as _se:
    import logging as _slog
    _slog.getLogger().warning("security middleware skipped: %s", _se)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)

def _now() -> str: return datetime.now(timezone.utc).isoformat()
EVENTS: list = []
MAX_EVENTS = 10000  # bounded to prevent OOM


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "analytics-service"}


class Event(BaseModel):
    name: str
    properties: dict = {}
    userId: Optional[str] = None
    deviceId: Optional[str] = None


@app.post("/analytics/events", status_code=202)
def ingest(body: Event, claims: dict = Depends(_require_auth)):
    if len(body.name) > 100:
        return {"received": False, "error": "name too long"}
    EVENTS.append({**body.model_dump(), "at": _now()})
    if len(EVENTS) > MAX_EVENTS:
        del EVENTS[:len(EVENTS) - MAX_EVENTS]
    return {"received": True, "eventId": f"ev_{len(EVENTS)}"}


@app.get("/analytics/events/recent")
def recent(limit: int = 50):
    limit = max(1, min(limit, 500))
    return list(reversed(EVENTS[-limit:]))


@app.get("/analytics/watch-time/today")
def watch_time() -> dict[str, Any]:
    return {
        "totalMinutesWatched": 47,
        "topVideos": [
            {"videoId": "vid_001", "title": "How we cut churn 38%…", "minutes": 22},
            {"videoId": "vid_002", "title": "The Last Signal · E3", "minutes": 14},
            {"videoId": "vid_003", "title": "3 onboarding flows…", "minutes": 11},
        ],
    }
