"""Real WebAuthn (FIDO2) helpers. py_webauthn 2.5+."""
import base64
import json
import os
from typing import Any

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "distrebute.com")
RP_ORIGIN = os.getenv("WEBAUTHN_RP_ORIGIN", "http://localhost:8080")


def b64url_decode(s) -> bytes:
    if isinstance(s, bytes):
        return s
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s.encode())


def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def make_registration_options(user_id: bytes, email: str,
                              existing_credentials: list[bytes]) -> dict[str, Any]:
    opts = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user_id,
        user_name=email,
        user_display_name=email,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=c) for c in existing_credentials
        ],
    )
    return json.loads(options_to_json(opts))


def verify_registration(credential_json: dict, expected_challenge: bytes):
    return verify_registration_response(
        credential=credential_json,
        expected_challenge=expected_challenge,
        expected_origin=RP_ORIGIN,
        expected_rp_id=RP_ID,
        require_user_verification=False,
    )


def make_authentication_options(allow_credential_ids: list[bytes]) -> dict[str, Any]:
    opts = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=cid) for cid in allow_credential_ids
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return json.loads(options_to_json(opts))


def verify_authentication(credential_json: dict, expected_challenge: bytes,
                          credential_public_key: bytes, sign_count: int):
    return verify_authentication_response(
        credential=credential_json,
        expected_challenge=expected_challenge,
        expected_rp_id=RP_ID,
        expected_origin=RP_ORIGIN,
        credential_public_key=credential_public_key,
        credential_current_sign_count=sign_count,
        require_user_verification=False,
    )
