"""distrebute user-service. Verifies tokens via auth-service JWKS."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

import httpx
import jwt
from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

app = FastAPI(title="distrebute user-service", version="0.1.0")


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



@app.on_event("startup")
async def prime_jwks_cache():
    """Prefetch auth-service's JWKS on boot so first request doesn't block."""
    await _refresh_jwks_async()

JWKS_URL = os.getenv("JWT_PUBLIC_KEY_URL", "http://auth-service:8001/.well-known/jwks.json")
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}


async def _refresh_jwks_async():
    """Refresh JWKS asynchronously without blocking the event loop."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(JWKS_URL)
            _jwks_cache.update(r.json())
    except Exception as e:
        print(f"[jwks] async fetch failed: {e}")


def _get_jwks():
    """Returns cached JWKS. If empty (first call), does a quick sync fetch as fallback."""
    if not _jwks_cache["keys"]:
        try:
            _jwks_cache.update(httpx.get(JWKS_URL, timeout=2.0).json())
        except Exception as e:
            print(f"[jwks] fetch failed: {e}")
    return _jwks_cache


def _verify(token: str) -> dict:
    jwks = _get_jwks()
    for key_dict in jwks.get("keys", []):
        try:
            pub = jwt.algorithms.RSAAlgorithm.from_jwk(key_dict)
            return jwt.decode(token, pub, algorithms=["RS256"],
                              options={"verify_aud": False})
        except Exception:
            continue
    raise HTTPException(status_code=401, detail="token verification failed")


def _user(authorization):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer")
    return _verify(authorization.split(" ", 1)[1])


def _hash_pin(pin: str, salt: bytes = None):
    """scrypt — slow & memory-hard. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return h, salt


def _verify_pin(pin: str, stored_hash: bytes, salt: bytes) -> bool:
    h, _ = _hash_pin(pin, salt)
    return hmac.compare_digest(h, stored_hash)


PROFILES: dict = {}
PRIVACY: dict = {}
DEVICES: dict = {}
PINS: dict = {}
PARENTAL: dict = {}


def _now(): return datetime.now(timezone.utc).isoformat()


def _seed(uid: str):
    if uid in PROFILES: return
    PROFILES[uid] = [
        {"id": "prof_main", "name": "Sree", "avatarUrl": "", "age": None,
         "isKidProfile": False, "ageRatingCap": "A"},
    ]
    PRIVACY[uid] = {
        "watchHistory": True, "personalization": True, "voiceSearchHistory": False,
        "adPersonalization": False, "locationForLive": True, "crashDiagnostics": True,
    }
    DEVICES[uid] = [
        {"id": "dev_current", "name": "iPhone 15 Pro · Safari", "type": "phone",
         "location": "Mumbai, IN", "ipMasked": "49.34.•••.••",
         "lastActiveAt": _now(), "isCurrent": True, "isFlagged": False},
        {"id": "dev_tv", "name": "Samsung Smart TV · distrebute app", "type": "tv",
         "location": "Hyderabad home", "ipMasked": "117.96.•••.••",
         "lastActiveAt": _now(), "isCurrent": False, "isFlagged": False},
    ]


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "user-service"}


@app.get("/users/me")
def me(authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    return {
        "id": claims["sub"], "email": claims.get("email"), "displayName": "Sree",
        "avatarUrl": "", "country": "IN", "language": "en", "createdAt": _now(),
    }


@app.get("/users/me/profiles")
def list_profiles(authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    return PROFILES[claims["sub"]]


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    avatarUrl: str = Field("", max_length=500)
    age: Optional[int] = Field(None, ge=0, le=120)
    isKidProfile: bool = False
    ageRatingCap: str = Field("A", max_length=10)


@app.post("/users/me/profiles", status_code=201)
def create_profile(body: ProfileCreate, authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    if len(PROFILES[claims["sub"]]) >= 5:
        raise HTTPException(status_code=400, detail="max 5 profiles per account")
    new = body.model_dump()
    new["id"] = f"prof_{secrets.token_hex(4)}"
    PROFILES[claims["sub"]].append(new)
    return new


class ParentalControlsModel(BaseModel):
    ageRatingCap: str = Field("U/A 13+", max_length=10)
    dailyScreenTimeMinutes: int = Field(120, ge=0, le=1440)
    weeklySchedule: list = []
    allowedCategories: list = Field([], max_length=50)
    blockedCategories: list = Field([], max_length=50)
    pinRequiredToExit: bool = True


@app.put("/users/me/profiles/{profile_id}/parental")
def set_parental(profile_id: str, body: ParentalControlsModel,
                 authorization: Optional[str] = Header(None)):
    _user(authorization)
    PARENTAL[profile_id] = body.model_dump()
    return PARENTAL[profile_id]


class PinBody(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


@app.post("/users/me/pin")
def set_pin(body: PinBody, authorization: Optional[str] = Header(None)):
    claims = _user(authorization)
    if not body.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be all digits")
    if len(set(body.pin)) == 1:
        raise HTTPException(status_code=400, detail="PIN cannot be all same digit")
    h, salt = _hash_pin(body.pin)
    PINS[claims["sub"]] = {"hash": h, "salt": salt}
    return Response(status_code=204)


class PinVerify(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


@app.post("/users/me/pin/verify")
def verify_pin(body: PinVerify, authorization: Optional[str] = Header(None)):
    claims = _user(authorization)
    stored = PINS.get(claims["sub"])
    if not stored:
        raise HTTPException(status_code=404, detail="no PIN set")
    if not _verify_pin(body.pin, stored["hash"], stored["salt"]):
        raise HTTPException(status_code=401, detail="incorrect PIN")
    return {"verified": True}


class PrivacyModel(BaseModel):
    watchHistory: bool
    personalization: bool
    voiceSearchHistory: bool
    adPersonalization: bool
    locationForLive: bool
    crashDiagnostics: bool


@app.get("/users/me/privacy")
def get_privacy(authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    return PRIVACY[claims["sub"]]


@app.put("/users/me/privacy")
def put_privacy(body: PrivacyModel, authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    PRIVACY[claims["sub"]] = body.model_dump()
    return PRIVACY[claims["sub"]]


@app.post("/users/me/data-export", status_code=202)
def data_export(authorization: Optional[str] = Header(None)):
    _user(authorization)
    return {"jobId": f"exp_{secrets.token_hex(8)}",
            "estimatedReadyAt": _now()}


@app.delete("/users/me/account", status_code=202)
def delete_account(authorization: Optional[str] = Header(None)):
    _user(authorization)
    return {"status": "scheduled", "graceUntil": "30 days"}


@app.get("/users/me/devices")
def devices(authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    return DEVICES[claims["sub"]]


# /all MUST come before /{device_id}
@app.delete("/users/me/devices/all")
def signout_all(authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    DEVICES[claims["sub"]] = [d for d in DEVICES[claims["sub"]] if d["isCurrent"]]
    return Response(status_code=204)


@app.delete("/users/me/devices/{device_id}")
def signout_device(device_id: str, authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    if len(device_id) > 100:
        raise HTTPException(status_code=400, detail="invalid device_id")
    DEVICES[claims["sub"]] = [d for d in DEVICES[claims["sub"]] if d["id"] != device_id]
    return Response(status_code=204)


@app.post("/users/me/devices/{device_id}/not-me", status_code=202)
def not_me(device_id: str, authorization: Optional[str] = Header(None)):
    claims = _user(authorization); _seed(claims["sub"])
    DEVICES[claims["sub"]] = [d for d in DEVICES[claims["sub"]] if d["id"] != device_id]
    return {"status": "recovery flow initiated",
            "advice": "rotate passkey, sign out all"}
