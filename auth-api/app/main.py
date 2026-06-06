"""distrebute auth-service v0.3 — real WebAuthn + SQLAlchemy persistence for users+creds."""
import base64
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
from typing import Literal, Optional

import pyotp
import qrcode
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from . import jwt_utils
from . import webauthn_helpers as wa
from . import repo
from . import sso_helpers
from .db import init_db, SessionLocal

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="distrebute auth-service", version="0.3.0", lifespan=lifespan)


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

# ---------- Rate limiting (in-memory; use Redis in prod for cross-replica) ----------
_RATE_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMITS = {
    "/auth/email/start":       (5, 60),
    "/auth/email/verify":      (10, 60),
    "/auth/passkey/register/challenge": (10, 60),
    "/auth/passkey/register/verify":    (10, 60),
    "/auth/passkey/login/challenge":    (10, 60),
    "/auth/passkey/login/verify":       (10, 60),
    "/auth/sso/apple":         (10, 60),
    "/auth/sso/google":        (10, 60),
    "/auth/sso/facebook":      (10, 60),
    "/auth/refresh":           (20, 60),
}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    limit = _RATE_LIMITS.get(request.url.path)
    if limit:
        max_req, window = limit
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}|{request.url.path}"
        now_t = time.time()
        bucket = _RATE_BUCKETS.setdefault(key, [])
        bucket[:] = [t for t in bucket if t > now_t - window]
        if len(bucket) >= max_req:
            return JSONResponse(
                status_code=429,
                content={"detail": f"rate limit: {max_req}/{window}s"},
                headers={"Retry-After": str(window)},
            )
        bucket.append(now_t)
    return await call_next(request)


# ---------- Short-lived state still in memory (OTPs, challenges, TOTP) ----------
PASSKEY_REG_CHALLENGES: dict[str, dict] = {}
PASSKEY_LOGIN_CHALLENGES: dict[str, dict] = {}
EMAIL_OTPS: dict[str, dict] = {}
TOTP_SECRETS: dict[str, str] = {}
ENABLED_2FA: set = set()
SECURITY_EVENTS: list = []
RECOVERY_CODES: dict[str, list] = {}


def _now_iso(): return datetime.now(timezone.utc).isoformat()


async def get_db() -> AsyncSession:
    async with SessionLocal() as s:
        yield s


def _record_event(user_id, type_, **extras):
    ev = {"id": f"evt_{secrets.token_hex(6)}", "userId": user_id, "type": type_,
          "at": _now_iso(), "device": extras.get("device", "Unknown"),
          "location": extras.get("location", "Unknown"),
          "ipMasked": extras.get("ipMasked", "•.•.•.•"),
          "flagged": extras.get("flagged", False)}
    SECURITY_EVENTS.append(ev)
    return ev


async def _require_user(authorization: Optional[str], db: AsyncSession):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        claims = jwt_utils.verify(authorization.split(" ", 1)[1])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")
    user = await repo.get_user_by_id(db, claims["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int = jwt_utils.ACCESS_TTL


def _issue_pair(user, method):
    _record_event(user.id, "signin", device=method)
    return TokenPair(
        accessToken=jwt_utils.issue_access_token(
            user.id, {"email": user.email, "method": method}),
        refreshToken=jwt_utils.issue_refresh_token(user.id),
    )


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "auth-service", "version": "0.3.0"}


@app.get("/.well-known/jwks.json")
def jwks(): return jwt_utils.jwks()


# ---------- Passkey REGISTRATION ----------
class PasskeyEmail(BaseModel):
    email: EmailStr


@app.post("/auth/passkey/register/challenge")
async def passkey_register_challenge(req: PasskeyEmail,
                                      authorization: Optional[str] = Header(None),
                                      db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    if user.email != req.email:
        raise HTTPException(status_code=403, detail="email does not match logged-in user")
    existing = [wa.b64url_decode(c.credential_id) for c in user.credentials]
    opts = wa.make_registration_options(
        user_id=user.id.encode(),
        email=user.email,
        existing_credentials=existing,
    )
    PASSKEY_REG_CHALLENGES[user.email] = {
        "challenge": wa.b64url_decode(opts["challenge"]),
        "exp": time.time() + 300,
    }
    return opts


class PasskeyRegisterVerify(BaseModel):
    email: EmailStr
    credential: dict


@app.post("/auth/passkey/register/verify")
async def passkey_register_verify(req: PasskeyRegisterVerify,
                                   authorization: Optional[str] = Header(None),
                                   db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    if user.email != req.email:
        raise HTTPException(status_code=403, detail="email mismatch")
    pending = PASSKEY_REG_CHALLENGES.pop(req.email, None)
    if not pending or pending["exp"] < time.time():
        raise HTTPException(status_code=400, detail="no active registration challenge")
    try:
        verified = wa.verify_registration(
            credential_json=req.credential,
            expected_challenge=pending["challenge"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"registration failed: {e}")
    await repo.add_credential(
        db, user_id=user.id,
        credential_id=wa.b64url_encode(verified.credential_id),
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
    )
    _record_event(user.id, "passkey_registered")
    return {"status": "credential registered",
            "credentialId": wa.b64url_encode(verified.credential_id)}


# ---------- Passkey LOGIN ----------
@app.post("/auth/passkey/login/challenge")
async def passkey_login_challenge(req: PasskeyEmail, db: AsyncSession = Depends(get_db)):
    user = await repo.get_user_by_email(db, req.email)
    if not user or not user.credentials:
        raise HTTPException(status_code=404, detail="no passkey registered for this email")
    allow = [wa.b64url_decode(c.credential_id) for c in user.credentials]
    opts = wa.make_authentication_options(allow_credential_ids=allow)
    PASSKEY_LOGIN_CHALLENGES[req.email] = {
        "challenge": wa.b64url_decode(opts["challenge"]),
        "exp": time.time() + 300,
    }
    return opts


class PasskeyLoginVerify(BaseModel):
    email: EmailStr
    credential: dict


@app.post("/auth/passkey/login/verify")
async def passkey_login_verify(req: PasskeyLoginVerify,
                                db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await repo.get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    pending = PASSKEY_LOGIN_CHALLENGES.pop(req.email, None)
    if not pending or pending["exp"] < time.time():
        raise HTTPException(status_code=400, detail="no active login challenge")
    cred_id = req.credential.get("id") or req.credential.get("rawId")
    if not cred_id:
        raise HTTPException(status_code=400, detail="credential.id missing")
    stored = next((c for c in user.credentials if c.credential_id == cred_id), None)
    if not stored:
        raise HTTPException(status_code=404, detail="unknown credential")
    try:
        verified = wa.verify_authentication(
            credential_json=req.credential,
            expected_challenge=pending["challenge"],
            credential_public_key=stored.public_key,
            sign_count=stored.sign_count,
        )
    except Exception as e:
        _record_event(user.id, "passkey_failed", flagged=True)
        raise HTTPException(status_code=401, detail=f"signature verify failed: {e}")
    await repo.update_sign_count(db, stored, verified.new_sign_count)
    return _issue_pair(user, method="passkey")


# ---------- SSO ----------
class SSORequest(BaseModel):
    idToken: Optional[str] = Field(None, max_length=10000)
    authCode: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None


@app.post("/auth/sso/{provider}")
async def sso(provider: Literal["apple", "google", "facebook"],
              req: SSORequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Validates provider id_token (Apple/Google) or access_token (Facebook).
    Falls back to email-in-body ONLY when DEV_MODE=true AND no provider keys are set."""
    try:
        email = sso_helpers.verify_provider(provider, req.idToken, req.authCode)
    except sso_helpers.SSOError as e:
        no_keys = (
            (provider == "google" and not sso_helpers.GOOGLE_CLIENT_ID)
            or (provider == "apple" and not sso_helpers.APPLE_CLIENT_ID)
            or (provider == "facebook" and not sso_helpers.FACEBOOK_APP_ID)
        )
        if DEV_MODE and no_keys and req.email:
            email = req.email  # dev-mode fallback
        else:
            raise HTTPException(status_code=400, detail=f"sso failed: {e}")
    user = await repo.get_or_create_user(db, email)
    return _issue_pair(user, method=f"sso:{provider}")


# ---------- Email OTP ----------
class EmailStartRequest(BaseModel):
    email: EmailStr


@app.post("/auth/email/start", status_code=202)
def email_start(req: EmailStartRequest):
    code = f"{secrets.randbelow(1000000):06d}"
    EMAIL_OTPS[req.email] = {"code": code, "exp": time.time() + 600, "attempts": 0}
    print(f"[email_otp] {req.email} → code={code}")
    resp = {"status": "code sent"}
    if DEV_MODE:
        resp["_devCode"] = code
    return resp


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


@app.post("/auth/email/verify")
async def email_verify(req: EmailVerifyRequest,
                        db: AsyncSession = Depends(get_db)) -> TokenPair:
    pending = EMAIL_OTPS.get(req.email)
    if not pending or pending["exp"] < time.time():
        raise HTTPException(status_code=400, detail="no valid code")
    pending["attempts"] += 1
    if pending["attempts"] > 5:
        EMAIL_OTPS.pop(req.email, None)
        raise HTTPException(status_code=429, detail="too many attempts; request new code")
    if pending["code"] != req.code:
        raise HTTPException(status_code=400, detail="incorrect code")
    EMAIL_OTPS.pop(req.email)
    user = await repo.get_or_create_user(db, req.email)
    return _issue_pair(user, method="email_otp")


# ---------- Refresh ----------
class RefreshRequest(BaseModel):
    refreshToken: str = Field(..., max_length=5000)


@app.post("/auth/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        claims = jwt_utils.verify(req.refreshToken)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    if claims.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="not a refresh token")
    user = await repo.get_user_by_id(db, claims["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return _issue_pair(user, method="refresh")


# ---------- 2FA ----------
@app.post("/auth/2fa/setup")
async def twofa_setup(authorization: Optional[str] = Header(None),
                       db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    secret = pyotp.random_base32()
    TOTP_SECRETS[user.id] = secret
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="distrebute.com")
    img = qrcode.make(uri)
    buf = BytesIO(); img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    codes = [secrets.token_hex(4) for _ in range(10)]
    RECOVERY_CODES[user.id] = codes
    return {"qrPngBase64": qr_b64, "secret": secret, "recoveryCodes": codes}


class TOTPVerify(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


@app.post("/auth/2fa/verify")
async def twofa_verify(req: TOTPVerify, authorization: Optional[str] = Header(None),
                        db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    secret = TOTP_SECRETS.get(user.id)
    if not secret:
        raise HTTPException(status_code=400, detail="2FA not started")
    if not pyotp.TOTP(secret).verify(req.code):
        raise HTTPException(status_code=400, detail="incorrect TOTP code")
    ENABLED_2FA.add(user.id)
    return {"status": "2FA enabled"}


@app.get("/auth/security/health")
async def health(authorization: Optional[str] = Header(None),
                  db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    checks = []; score = 0
    def add(key, label, status, weight, detail=""):
        nonlocal score
        if status == "done": score += weight
        checks.append({"key": key, "label": label, "status": status, "detail": detail})
    add("passkey_set", "Passkey set up",
        "done" if user.passkey_enabled else "todo", 25)
    add("twofa", "2-step verification",
        "done" if user.id in ENABLED_2FA else "todo", 25)
    add("recovery_email", "Recovery email verified", "done", 15, user.email)
    add("recovery_codes", "Backup recovery codes",
        "warn" if user.id in ENABLED_2FA and user.id not in RECOVERY_CODES else "done", 20)
    add("phone", "Phone number", "todo", 15)
    grade = ("perfect" if score >= 100 else "strong" if score >= 75
             else "moderate" if score >= 40 else "weak")
    return {"score": score, "grade": grade, "checks": checks}


@app.get("/auth/events")
async def events(authorization: Optional[str] = Header(None), limit: int = 20,
                  db: AsyncSession = Depends(get_db)):
    user = await _require_user(authorization, db)
    limit = max(1, min(limit, 100))
    return list(reversed(
        [e for e in SECURITY_EVENTS if e.get("userId") == user.id][-limit:]
    ))


@app.post("/internal/introspect")
def introspect(req: Request):
    auth = req.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer")
    try:
        claims = jwt_utils.verify(auth.split(" ", 1)[1])
        return {"active": True, **claims}
    except Exception as e:
        return {"active": False, "reason": str(e)}
