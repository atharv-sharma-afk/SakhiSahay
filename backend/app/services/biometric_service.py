"""App lock backed by WebAuthn platform authenticators (Touch ID / Face ID / Windows Hello).

How it works
------------
* The browser calls ``navigator.credentials.create`` / ``.get`` with options we
  generate here. The operating system performs the biometric check; we never see
  biometric data, only a public key (at registration) and signatures (at unlock).
* Every challenge is single-use and expires after a few minutes.
* A successful, server-verified assertion yields a short-lived **unlock token**.
  While the lock is enabled, all health-data routes require that token
  (see ``app.api.deps``), so the lock is enforced by the API, not just the UI.

Stores are in-process dictionaries: the MVP runs as a single uvicorn worker and
tokens are meant to die with the process. Swap for Redis/DB when scaling out.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.db import models

CHALLENGE_TTL_SECONDS = 300
_TOKEN_BYTES = 32


class BiometricError(ValueError):
    """Raised for any client-correctable problem (bad origin, stale challenge, bad signature)."""


@dataclass
class _Challenge:
    value: bytes
    purpose: str  # "register" | "authenticate"
    expires_at: float


@dataclass
class _UnlockToken:
    user_id: str
    expires_at: float


class _Stores:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.challenges: dict[str, _Challenge] = {}
        self.tokens: dict[str, _UnlockToken] = {}

    # ---- challenges ---------------------------------------------------------
    def put_challenge(self, user_id: str, purpose: str, value: bytes) -> None:
        with self._lock:
            self._sweep()
            self.challenges[user_id] = _Challenge(value, purpose, time.time() + CHALLENGE_TTL_SECONDS)

    def pop_challenge(self, user_id: str, purpose: str) -> bytes:
        with self._lock:
            item = self.challenges.pop(user_id, None)
        if item is None or item.purpose != purpose:
            raise BiometricError("No pending request. Start again.")
        if item.expires_at < time.time():
            raise BiometricError("The request expired. Start again.")
        return item.value

    # ---- unlock tokens -----------------------------------------------------
    def issue_token(self, user_id: str, ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        with self._lock:
            self._sweep()
            self.tokens[token] = _UnlockToken(user_id, time.time() + ttl_seconds)
        return token

    def token_is_valid(self, user_id: str, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            item = self.tokens.get(token)
            if item is None:
                return False
            if item.expires_at < time.time():
                self.tokens.pop(token, None)
                return False
            return item.user_id == user_id

    def revoke_user_tokens(self, user_id: str) -> None:
        with self._lock:
            for key in [k for k, v in self.tokens.items() if v.user_id == user_id]:
                self.tokens.pop(key, None)

    def _sweep(self) -> None:
        now = time.time()
        for key in [k for k, v in self.challenges.items() if v.expires_at < now]:
            self.challenges.pop(key, None)
        for key in [k for k, v in self.tokens.items() if v.expires_at < now]:
            self.tokens.pop(key, None)


_stores = _Stores()


def reset_stores_for_tests() -> None:
    global _stores
    _stores = _Stores()


# ---------------------------------------------------------------- origin / rp id


def resolve_rp(origin: str | None, configured_rp_id: str, allowed_origins: list[str]) -> tuple[str, str]:
    """Return (rp_id, expected_origin) for this request.

    The RP ID must be the page's host (or a registrable suffix of it). We take it
    from configuration when set, otherwise from the request's Origin header, and
    we only accept origins that are explicitly allowed (or loopback in dev).
    """
    if not origin:
        raise BiometricError("Missing Origin header")
    parsed = urlparse(origin)
    host = parsed.hostname or ""
    if not host:
        raise BiometricError("Invalid Origin header")
    is_loopback = host in {"localhost", "127.0.0.1", "::1"}
    if origin not in allowed_origins and not is_loopback:
        raise BiometricError("This origin is not allowed to use the app lock")
    if parsed.scheme != "https" and not is_loopback:
        raise BiometricError("Biometric unlock requires HTTPS (or localhost)")
    rp_id = configured_rp_id or host
    if rp_id != host and not host.endswith("." + rp_id):
        raise BiometricError("Origin does not match the configured relying-party id")
    return rp_id, origin


# ---------------------------------------------------------------- queries


def list_credentials(db: Session, user_id: str) -> list[models.WebAuthnCredential]:
    stmt = select(models.WebAuthnCredential).where(models.WebAuthnCredential.user_id == user_id)
    return list(db.scalars(stmt))


def is_unlocked(user: models.User, token: str | None) -> bool:
    """True when the lock is off, or the supplied token is a live token for this user."""
    if not user.biometric_lock_enabled:
        return True
    return _stores.token_is_valid(user.id, token)


# ---------------------------------------------------------------- registration


def registration_options(db: Session, user: models.User, rp_id: str, rp_name: str) -> dict:
    existing = list_credentials(db, user.id)
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=user.id.encode("utf-8"),
        user_name=user.display_name or "SakhiSahay user",
        user_display_name=user.display_name or "SakhiSahay user",
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c.credential_id) for c in existing],
        timeout=60000,
    )
    _stores.put_challenge(user.id, "register", options.challenge)
    return json.loads(options_to_json(options))


def complete_registration(
    db: Session,
    user: models.User,
    credential: dict,
    rp_id: str,
    expected_origin: str,
    label: str | None,
    token_ttl_seconds: int,
) -> tuple[models.WebAuthnCredential, str]:
    challenge = _stores.pop_challenge(user.id, "register")
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            require_user_verification=True,
        )
    except InvalidRegistrationResponse as exc:
        raise BiometricError(f"Device verification failed: {exc}") from exc

    transports = credential.get("response", {}).get("transports") if isinstance(credential, dict) else None
    record = models.WebAuthnCredential(
        user_id=user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=",".join(transports) if transports else None,
        device_type=str(verified.credential_device_type.value) if verified.credential_device_type else None,
        backed_up=bool(verified.credential_backed_up),
        label=(label or "").strip()[:80] or None,
    )
    db.add(record)
    user.biometric_lock_enabled = True
    db.commit()
    db.refresh(record)
    # Registering required a successful biometric check, so the session is unlocked.
    token = _stores.issue_token(user.id, token_ttl_seconds)
    return record, token


# ---------------------------------------------------------------- authentication


def authentication_options(db: Session, user: models.User, rp_id: str) -> dict:
    creds = list_credentials(db, user.id)
    if not creds:
        raise BiometricError("No device is registered for the app lock")
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[PublicKeyCredentialDescriptor(id=c.credential_id) for c in creds],
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=60000,
    )
    _stores.put_challenge(user.id, "authenticate", options.challenge)
    return json.loads(options_to_json(options))


def complete_authentication(
    db: Session,
    user: models.User,
    credential: dict,
    rp_id: str,
    expected_origin: str,
    token_ttl_seconds: int,
) -> str:
    challenge = _stores.pop_challenge(user.id, "authenticate")
    raw_id = credential.get("rawId") or credential.get("id") if isinstance(credential, dict) else None
    if not raw_id:
        raise BiometricError("Malformed credential")
    from webauthn.helpers import base64url_to_bytes

    try:
        cred_id = base64url_to_bytes(raw_id)
    except Exception as exc:  # noqa: BLE001 - any decode problem is a client error
        raise BiometricError("Malformed credential id") from exc

    record = db.scalar(
        select(models.WebAuthnCredential).where(
            models.WebAuthnCredential.user_id == user.id,
            models.WebAuthnCredential.credential_id == cred_id,
        )
    )
    if record is None:
        raise BiometricError("This device is not registered for the app lock")
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            credential_public_key=record.public_key,
            credential_current_sign_count=record.sign_count,
            require_user_verification=True,
        )
    except InvalidAuthenticationResponse as exc:
        raise BiometricError(f"Authentication failed: {exc}") from exc

    record.sign_count = verified.new_sign_count
    record.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return _stores.issue_token(user.id, token_ttl_seconds)


# ---------------------------------------------------------------- disable / lock


def disable_lock(db: Session, user: models.User) -> int:
    """Remove every registered device and turn the lock off. Caller must have verified identity."""
    creds = list_credentials(db, user.id)
    for cred in creds:
        db.delete(cred)
    user.biometric_lock_enabled = False
    db.commit()
    _stores.revoke_user_tokens(user.id)
    return len(creds)


def relock(user_id: str) -> None:
    """Invalidate every unlock token for the user (explicit lock from the UI)."""
    _stores.revoke_user_tokens(user_id)
