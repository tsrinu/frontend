"""RS256 JWT signing + JWKS exposure. Real implementation.

Other services verify our tokens by fetching the JWK set from
http://auth-service:8001/.well-known/jwks.json — no shared secret needed.
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEY_DIR = Path(os.getenv("JWT_KEY_DIR", "/app/keys"))
PRIVATE_PEM = KEY_DIR / "jwt_private.pem"
PUBLIC_PEM = KEY_DIR / "jwt_public.pem"
KEY_ID = "distrebute-2026-05"
ISSUER = os.getenv("JWT_ISSUER", "https://distrebute.com")
ACCESS_TTL = int(os.getenv("ACCESS_TTL_SECONDS", "900"))     # 15 min
REFRESH_TTL = int(os.getenv("REFRESH_TTL_SECONDS", "2592000"))  # 30 days


def _ensure_keypair() -> None:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if PRIVATE_PEM.exists() and PUBLIC_PEM.exists():
        return
    print(f"[jwt] generating new RSA-2048 keypair in {KEY_DIR}")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    PRIVATE_PEM.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLIC_PEM.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


_ensure_keypair()
PRIVATE_KEY = PRIVATE_PEM.read_bytes()
PUBLIC_KEY = PUBLIC_PEM.read_bytes()


def _b64url(n: int) -> str:
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwks() -> dict[str, Any]:
    pub = serialization.load_pem_public_key(PUBLIC_KEY)
    nums = pub.public_numbers()
    return {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": KEY_ID,
            "n": _b64url(nums.n),
            "e": _b64url(nums.e),
        }]
    }


def issue_access_token(sub: str, claims: dict[str, Any] | None = None) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": ISSUER, "sub": sub, "iat": now, "exp": now + ACCESS_TTL,
        "jti": str(uuid.uuid4()), **(claims or {}),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256", headers={"kid": KEY_ID})


def issue_refresh_token(sub: str) -> str:
    now = int(time.time())
    payload = {
        "iss": ISSUER, "sub": sub, "iat": now, "exp": now + REFRESH_TTL,
        "jti": str(uuid.uuid4()), "typ": "refresh",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256", headers={"kid": KEY_ID})


def verify(token: str) -> dict[str, Any]:
    return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], issuer=ISSUER)
