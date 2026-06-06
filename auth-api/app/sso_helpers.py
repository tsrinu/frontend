"""Real id_token validation for Apple / Google / Facebook SSO.

Closes the 🔴 CRITICAL "anyone can claim any email" hole by verifying the
provider's signature on the id_token (or access_token for Facebook).
"""
import os
from typing import Optional

import httpx
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token as g_id_token


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")


class SSOError(Exception):
    """Raised when an id_token / access_token can't be validated."""


def verify_google(id_token_jwt: str) -> str:
    """Verify a Google id_token. Returns the verified email."""
    if not GOOGLE_CLIENT_ID:
        raise SSOError("GOOGLE_CLIENT_ID not configured")
    try:
        payload = g_id_token.verify_oauth2_token(
            id_token_jwt, g_requests.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=10,
        )
    except Exception as e:
        raise SSOError(f"google id_token invalid: {e}")
    # Required claims per Google's docs
    if payload.get("aud") != GOOGLE_CLIENT_ID:
        raise SSOError("aud mismatch")
    if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise SSOError("iss not google")
    if not payload.get("email_verified"):
        raise SSOError("google email not verified")
    email = payload.get("email", "").lower()
    if not email:
        raise SSOError("no email in token")
    return email


def verify_apple(id_token_jwt: str) -> str:
    """Verify Apple id_token. Requires Apple JWKS fetch + ES256 verify."""
    if not APPLE_CLIENT_ID:
        raise SSOError("APPLE_CLIENT_ID not configured")
    import jwt as pyjwt
    try:
        jwks_data = httpx.get(
            "https://appleid.apple.com/auth/keys", timeout=3.0
        ).json()
        unverified_header = pyjwt.get_unverified_header(id_token_jwt)
        kid = unverified_header["kid"]
        key_dict = next((k for k in jwks_data["keys"] if k["kid"] == kid), None)
        if not key_dict:
            raise SSOError(f"apple kid {kid} not in JWKS")
        public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_dict)
        payload = pyjwt.decode(
            id_token_jwt, public_key,
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,
            issuer="https://appleid.apple.com",
        )
    except Exception as e:
        raise SSOError(f"apple id_token invalid: {e}")
    email = payload.get("email", "").lower()
    if not email:
        raise SSOError("no email in apple token")
    if payload.get("email_verified") is False:
        raise SSOError("apple email not verified")
    return email


def verify_facebook(access_token: str) -> str:
    """Facebook uses opaque access_tokens; verify by hitting Graph API.

    Costs a network round-trip; cache the result if you call this often.
    """
    if not FACEBOOK_APP_ID:
        raise SSOError("FACEBOOK_APP_ID not configured")
    try:
        # Step 1: validate the token against the app
        r = httpx.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": access_token,
                "access_token": f"{FACEBOOK_APP_ID}|{os.getenv('FACEBOOK_APP_SECRET', '')}",
            },
            timeout=3.0,
        )
        data = r.json().get("data", {})
        if not data.get("is_valid"):
            raise SSOError("facebook token not valid")
        if data.get("app_id") != FACEBOOK_APP_ID:
            raise SSOError("facebook token issued for different app")
        # Step 2: fetch the user's email
        r = httpx.get(
            "https://graph.facebook.com/me",
            params={"fields": "email", "access_token": access_token},
            timeout=3.0,
        )
        email = r.json().get("email", "").lower()
        if not email:
            raise SSOError("no email returned (user didn't grant email permission?)")
        return email
    except SSOError:
        raise
    except Exception as e:
        raise SSOError(f"facebook validation failed: {e}")


def verify_provider(provider: str, id_token: Optional[str], access_token: Optional[str]) -> str:
    if provider == "google":
        if not id_token:
            raise SSOError("google requires idToken")
        return verify_google(id_token)
    if provider == "apple":
        if not id_token:
            raise SSOError("apple requires idToken")
        return verify_apple(id_token)
    if provider == "facebook":
        if not access_token:
            raise SSOError("facebook requires accessToken")
        return verify_facebook(access_token)
    raise SSOError(f"unknown provider: {provider}")
