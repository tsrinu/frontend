"""distrebute social-service (HTTP routes only)."""
import secrets
from datetime import datetime, timezone
from typing import Optional
import os
from fastapi import FastAPI, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

from ws import register_ws_routes, broadcast as ws_broadcast

app = FastAPI(title="distrebute social-service", version="0.1.0")


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

def _now(): return datetime.now(timezone.utc).isoformat()

FOLLOWS = {}
COMMENTS = {}
PARTIES = {}


register_ws_routes(app)


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "social-service"}


@app.post("/social/follow/{channel_id}")
def follow(channel_id: str, claims: dict = Depends(_require_auth)):
    FOLLOWS.setdefault("anonymous", set()).add(channel_id)
    return Response(status_code=204)


@app.delete("/social/follow/{channel_id}")
def unfollow(channel_id: str, claims: dict = Depends(_require_auth)):
    FOLLOWS.setdefault("anonymous", set()).discard(channel_id)
    return Response(status_code=204)


@app.get("/social/comments/{video_id}")
def comments(video_id: str, sort: str = "top"):
    if not COMMENTS.get(video_id):
        COMMENTS[video_id] = [
            {"id": "cmt_1", "videoId": video_id, "parentId": None,
             "body": "This is the founder teardown I needed.",
             "author": {"handle": "@aki", "displayName": "Aki T.",
                        "avatarUrl": "", "verified": False},
             "likes": 312, "createdAt": _now(), "pinned": False, "creatorHearted": True},
            {"id": "cmt_2", "videoId": video_id, "parentId": None,
             "body": "Timestamp 14:08 is gold.",
             "author": {"handle": "@nina", "displayName": "Nina L.",
                        "avatarUrl": "", "verified": True},
             "likes": 184, "createdAt": _now(), "pinned": False, "creatorHearted": False},
        ]
    return COMMENTS[video_id]


class CommentCreate(BaseModel):
    body: str
    parentId: Optional[str] = None


@app.post("/social/comments/{video_id}", status_code=201)
def post_comment(video_id: str, body: CommentCreate, claims: dict = Depends(_require_auth)):
    cmt = {
        "id": f"cmt_{secrets.token_hex(4)}", "videoId": video_id,
        "parentId": body.parentId, "body": body.body,
        "author": {"handle": "@you", "displayName": "You",
                   "avatarUrl": "", "verified": False},
        "likes": 0, "createdAt": _now(), "pinned": False, "creatorHearted": False,
    }
    COMMENTS.setdefault(video_id, []).insert(0, cmt)
    return cmt


class PartyCreate(BaseModel):
    videoId: str
    inviteOnly: bool = False


@app.post("/social/watch-party", status_code=201)
def create_party(body: PartyCreate, claims: dict = Depends(_require_auth)):
    rid = f"party_{secrets.token_hex(6)}"
    PARTIES[rid] = {
        "roomId": rid, "videoId": body.videoId, "hostUserId": "anonymous",
        "inviteUrl": f"http://localhost:8080/watch-party/{rid}",
        "participants": [], "positionSec": 0, "playing": False,
    }
    return PARTIES[rid]


@app.post("/social/watch-party/{room_id}/join")
def join_party(room_id: str, claims: dict = Depends(_require_auth)):
    party = PARTIES.get(room_id)
    if not party:
        return {"error": "room not found"}
    return {"wsUrl": f"ws://localhost:8114/party/{room_id}",
            "participants": party["participants"]}


class React(BaseModel):
    emoji: str


@app.post("/social/watch-party/{room_id}/react")
async def react(room_id: str, body: React, claims: dict = Depends(_require_auth)):
    await ws_broadcast(room_id, {"type": "reaction", "emoji": body.emoji})
    return Response(status_code=204)
