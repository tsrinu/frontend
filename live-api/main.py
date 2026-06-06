"""distrebute live-service."""
import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

from ws import register_ws_routes

app = FastAPI(title="distrebute live-service", version="0.1.0")


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
register_ws_routes(app)

def _now(): return datetime.now(timezone.utc).isoformat()

STREAMS = {"stream_demo": {
    "id": "stream_demo", "channelId": "ch_mira",
    "title": "Cooking IRL: chana masala",
    "thumbnailUrl": "", "viewerCount": 12438,
    "tags": ["Food & Drink", "English", "Cozy"],
    "status": "live", "startedAt": _now(),
}}
POLLS: dict = {}
PREDICTIONS: dict = {}


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "live-service"}


@app.get("/live/streams/{stream_id}")
def get_stream(stream_id: str):
    if len(stream_id) > 100:
        raise HTTPException(status_code=400, detail="invalid stream_id")
    s = STREAMS.get(stream_id)
    if not s:
        s = {**STREAMS["stream_demo"], "id": stream_id}
    return s


@app.get("/live/streams/{stream_id}/chat")
def chat_ticket(stream_id: str):
    return {"wsUrl": f"ws://localhost:8113/live/{stream_id}/chat",
            "token": secrets.token_urlsafe(16)}


class PollCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=200)
    options: list = Field(..., min_length=2, max_length=8)
    durationSec: int = Field(90, ge=10, le=600)


@app.post("/live/streams/{stream_id}/poll", status_code=201)
def create_poll(stream_id: str, body: PollCreate, claims: dict = Depends(_require_auth)):
    for o in body.options:
        if not isinstance(o, str) or len(o) > 100:
            raise HTTPException(status_code=400, detail="each option must be ≤100 char string")
    pid = f"poll_{secrets.token_hex(4)}"
    poll = {
        "id": pid, "streamId": stream_id, "question": body.question,
        "options": [{"text": o, "votes": 0, "percent": 0.0} for o in body.options],
        "endsAt": (datetime.now(timezone.utc) + timedelta(seconds=body.durationSec)).isoformat(),
    }
    POLLS[pid] = poll
    return poll


class PollVote(BaseModel):
    optionIndex: int = Field(..., ge=0, le=100)


@app.post("/live/streams/{stream_id}/poll/{poll_id}/vote")
def vote_poll(stream_id: str, poll_id: str, body: PollVote, claims: dict = Depends(_require_auth)):
    poll = POLLS.get(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="poll not found")
    if not (0 <= body.optionIndex < len(poll["options"])):
        raise HTTPException(status_code=400, detail="optionIndex out of range")
    poll["options"][body.optionIndex]["votes"] += 1
    total = sum(o["votes"] for o in poll["options"])
    for o in poll["options"]:
        o["percent"] = round(o["votes"] / total * 100, 1) if total else 0.0
    return Response(status_code=204)


class PredictionCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=200)
    outcomes: list = Field(..., min_length=2, max_length=4)
    durationSec: int = Field(120, ge=10, le=600)


@app.post("/live/streams/{stream_id}/prediction", status_code=201)
def create_prediction(stream_id: str, body: PredictionCreate, claims: dict = Depends(_require_auth)):
    pid = f"pred_{secrets.token_hex(4)}"
    pred = {
        "id": pid, "streamId": stream_id, "question": body.question,
        "outcomes": [{**o, "channelPointsStaked": 0, "odds": 1.0} for o in body.outcomes],
        "endsAt": (datetime.now(timezone.utc) + timedelta(seconds=body.durationSec)).isoformat(),
        "status": "open",
    }
    PREDICTIONS[pid] = pred
    return pred
