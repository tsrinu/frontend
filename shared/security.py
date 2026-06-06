"""Shared security middleware + helpers for all distrebute APIs.

Provides:
  - Security headers (X-Frame-Options, HSTS, X-Content-Type-Options, etc.)
  - Request size limit (DoS prevention)
  - Request ID for tracing
  - JWT verify dependency (Bearer token → claims dict)
  - Production-mode guard (refuses to start with DEV_MODE=true on a production-looking env)
  - /docs hidden in production
"""
import os
import uuid
import logging
import time
from typing import Optional

import httpx
import jwt
from fastapi import HTTPException, Header, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Config (env-driven)
# ────────────────────────────────────────────────────────────────
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(1 * 1024 * 1024)))  # 1 MB default
JWKS_URL = os.getenv("JWT_PUBLIC_KEY_URL", "http://auth-api:8001/.well-known/jwks.json")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").lower()


# ────────────────────────────────────────────────────────────────
# Production guard — call from each main.py at startup
# ────────────────────────────────────────────────────────────────
def production_guard():
    """Refuse to boot if DEV_MODE=true on a production-looking environment.
    Run at import time. Loud failure beats silent _devCode leaks."""
    if DEV_MODE and APP_ENV in ("production", "prod", "live"):
        raise RuntimeError(
            "DEV_MODE=true is FORBIDDEN when APP_ENV=production. "
            "Set DEV_MODE=false in your .env.production."
        )


# ────────────────────────────────────────────────────────────────
# Middleware: security headers + request ID + size limit
# ────────────────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended response headers on every response."""

    async def dispatch(self, request: Request, call_next):
        # Generate / propagate request ID
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # HSTS only on HTTPS — Caddy/nginx adds the actual cert; this header is the policy
        if request.url.scheme == "https" or os.getenv("FORCE_HSTS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # Don't leak server identity (starlette MutableHeaders: del-by-key)
        if "server" in response.headers:
            del response.headers["server"]
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than MAX_BODY_BYTES at the edge to prevent DoS."""

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"request body exceeds {MAX_BODY_BYTES} bytes"},
            )
        return await call_next(request)


def install_security(app, hide_docs_in_prod: bool = True):
    """One-call setup for any distrebute API.
    Adds middleware + optionally hides /docs in production.

    Usage:
        from security import install_security
        install_security(app)
    """
    production_guard()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    if hide_docs_in_prod and APP_ENV in ("production", "prod", "live"):
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None
        log.info("docs hidden (APP_ENV=production)")


# ────────────────────────────────────────────────────────────────
# JWT verification helper — for any API that needs to verify
# tokens issued by auth-api
# ────────────────────────────────────────────────────────────────
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL = 3600  # refresh hourly


def _refresh_jwks():
    """Sync refresh — call sparingly; cache is hourly."""
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.get(JWKS_URL)
            _jwks_cache.clear()
            _jwks_cache.update(r.json())
            _jwks_cache["fetched_at"] = time.time()
    except Exception as e:
        log.warning("jwks refresh failed: %s", e)


def _get_jwks() -> dict:
    if not _jwks_cache.get("keys") or (time.time() - _jwks_cache.get("fetched_at", 0)) > _JWKS_TTL:
        _refresh_jwks()
    return _jwks_cache


def verify_jwt(token: str) -> dict:
    """Verify a JWT issued by auth-api. Returns claims (sub, email, etc.)."""
    jwks = _get_jwks()
    last_err = None
    for key_dict in jwks.get("keys", []):
        try:
            pub = jwt.algorithms.RSAAlgorithm.from_jwk(key_dict)
            return jwt.decode(token, pub, algorithms=["RS256"], options={"verify_aud": False})
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=401, detail=f"token verification failed: {last_err}")


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency. Requires a valid Bearer JWT; returns claims dict.

    Usage:
        from fastapi import Depends
        from security import require_auth
        @app.post('/protected')
        def handler(claims: dict = Depends(require_auth)):
            user_id = claims['sub']
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return verify_jwt(authorization.split(" ", 1)[1])


def require_auth_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Like require_auth but returns None if no token (vs 401). For endpoints
    where auth is optional but useful (e.g. personalized rec for logged-in users)."""
    if not authorization:
        return None
    try:
        return require_auth(authorization)
    except HTTPException:
        return None
