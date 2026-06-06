"""distrebute notification-service (stub).

In-app inbox, push preferences, daily smart digest.
Production: integrate APNS, FCM, SendGrid; consume Kafka topics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

app = FastAPI(title="distrebute notification-service", version="0.1.0")


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

now = lambda: datetime.now(timezone.utc).isoformat()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "notification-service"}


@app.get("/notifications/inbox")
def inbox(claims: dict = Depends(_require_auth)) -> list[dict[str, Any]]:
    return [
        {"id": "n_1", "type": "new_episode",
         "title": "The Last Signal · Episode 4 is out",
         "body": "Watch \"Witness\" now — 41 min.", "thumbnailUrl": "",
         "linkUrl": "/titles/last-signal", "unread": True, "createdAt": now()},
        {"id": "n_2", "type": "creator_live",
         "title": "Mira Kavi is live",
         "body": "Cooking IRL: chana masala from her grandmother's recipe.",
         "thumbnailUrl": "", "linkUrl": "/live/mira", "unread": True, "createdAt": now()},
        {"id": "n_3", "type": "security_alert",
         "title": "New sign-in attempt blocked",
         "body": "From Bengaluru, IN. Was this you?", "thumbnailUrl": "",
         "linkUrl": "/account/security", "unread": True, "createdAt": now()},
        {"id": "n_4", "type": "payout",
         "title": "Your May payout is ready: $14,820",
         "body": "Next payout scheduled May 31.", "thumbnailUrl": "",
         "linkUrl": "/studio/earnings", "unread": False, "createdAt": now()},
    ]


class NotificationPreferences(BaseModel):
    push: dict[str, Any] = {"enabled": True, "quietHours": {"start": "22:00", "end": "08:00"}}
    email: dict[str, bool] = {"weeklyDigest": True, "creatorActivity": True, "securityAlerts": True}
    smartDigest: dict[str, Any] = {"enabled": True, "dailyAt": "08:30"}


PREFS = NotificationPreferences()


@app.get("/notifications/preferences")
def get_prefs(claims: dict = Depends(_require_auth)) -> NotificationPreferences:
    return PREFS


@app.put("/notifications/preferences")
def set_prefs(body: NotificationPreferences, claims: dict = Depends(_require_auth)) -> NotificationPreferences:
    global PREFS
    PREFS = body
    return PREFS
