"""End-to-end tests for the WebAuthn app lock using a software authenticator.

The authenticator below does exactly what a platform authenticator does after
Touch ID / Face ID succeeds: it holds a P-256 key pair, builds authenticator
data, and signs ``authenticatorData || sha256(clientDataJSON)``. This proves the
server really verifies signatures, challenges, origins and counters - nothing
here is mocked on the verification side.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
from datetime import date, timedelta

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from app.services import biometric_service

ORIGIN = "http://localhost:3000"
RP_ID = "localhost"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class SoftwareAuthenticator:
    def __init__(self) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        self.sign_count = 0

    def _cose_public_key(self) -> bytes:
        nums = self.key.public_key().public_numbers()
        return cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")}
        )

    def create(self, options: dict, *, user_verified: bool = True) -> dict:
        client_data = json.dumps(
            {"type": "webauthn.create", "challenge": options["challenge"], "origin": ORIGIN, "crossOrigin": False}
        ).encode()
        flags = 0x01 | 0x40 | (0x04 if user_verified else 0)  # UP | AT | UV
        auth_data = (
            hashlib.sha256(RP_ID.encode()).digest()
            + bytes([flags])
            + struct.pack(">I", self.sign_count)
            + b"\x00" * 16
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + self._cose_public_key()
        )
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {
            "id": b64url(self.credential_id),
            "rawId": b64url(self.credential_id),
            "type": "public-key",
            "authenticatorAttachment": "platform",
            "clientExtensionResults": {},
            "response": {
                "clientDataJSON": b64url(client_data),
                "attestationObject": b64url(attestation),
                "transports": ["internal"],
            },
        }

    def get(self, options: dict, *, user_verified: bool = True, tamper: bool = False) -> dict:
        self.sign_count += 1
        client_data = json.dumps(
            {"type": "webauthn.get", "challenge": options["challenge"], "origin": ORIGIN, "crossOrigin": False}
        ).encode()
        flags = 0x01 | (0x04 if user_verified else 0)
        auth_data = hashlib.sha256(RP_ID.encode()).digest() + bytes([flags]) + struct.pack(">I", self.sign_count)
        signature = self.key.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        if tamper:
            signature = bytes([signature[0] ^ 0x01]) + signature[1:]
        return {
            "id": b64url(self.credential_id),
            "rawId": b64url(self.credential_id),
            "type": "public-key",
            "clientExtensionResults": {},
            "response": {
                "clientDataJSON": b64url(client_data),
                "authenticatorData": b64url(auth_data),
                "signature": b64url(signature),
                "userHandle": None,
            },
        }


H = {"Origin": ORIGIN}


@pytest.fixture(autouse=True)
def _fresh_lock_state(client):
    biometric_service.reset_stores_for_tests()
    yield
    # Make sure no test leaves the shared local user locked for the next test module.
    status = client.get("/api/auth/biometric/status").json()
    if status["enabled"]:
        from app.db import models
        from app.db.session import get_sessionmaker

        with get_sessionmaker()() as session:
            session.query(models.WebAuthnCredential).delete()
            for user in session.query(models.User).all():
                user.biometric_lock_enabled = False
            session.commit()
    biometric_service.reset_stores_for_tests()


def _enable(client, authenticator: SoftwareAuthenticator) -> str:
    opts = client.post("/api/auth/biometric/register/options", headers=H)
    assert opts.status_code == 200, opts.text
    options = opts.json()
    assert options["rp"]["id"] == RP_ID
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["authenticatorSelection"]["authenticatorAttachment"] == "platform"
    verified = client.post(
        "/api/auth/biometric/register/verify",
        json={"credential": authenticator.create(options), "label": "Test Mac"},
        headers=H,
    )
    assert verified.status_code == 201, verified.text
    return verified.json()["unlock_token"]


def test_status_defaults(client):
    body = client.get("/api/auth/biometric/status").json()
    assert body == {
        "enabled": False,
        "credential_count": 0,
        "lock_timeout_seconds": 0,
        "unlocked": True,
        "rp_name": "SakhiSahay",
    }


def test_register_requires_origin(client):
    assert client.post("/api/auth/biometric/register/options").status_code == 400
    bad = client.post("/api/auth/biometric/register/options", headers={"Origin": "http://evil.example"})
    assert bad.status_code == 400


def test_enable_lock_gates_health_routes_until_unlocked(client):
    authenticator = SoftwareAuthenticator()
    token = _enable(client, authenticator)

    status = client.get("/api/auth/biometric/status").json()
    assert status["enabled"] is True and status["credential_count"] == 1

    # Without a token: locked (423) - the lock is enforced by the API, not the UI.
    assert client.get("/api/tracker/periods").status_code == 423
    assert client.get("/api/profile").status_code == 423
    assert client.post("/api/tracker/symptoms", json={"record_date": date.today().isoformat(), "symptom": "calm"}).status_code == 423
    # A made-up token does not help
    assert client.get("/api/tracker/periods", headers={"X-Unlock-Token": "nope"}).status_code == 423
    # With the token issued at registration: allowed
    assert client.get("/api/tracker/periods", headers={"X-Unlock-Token": token}).status_code == 200

    # Explicit lock revokes the token
    assert client.post("/api/auth/biometric/lock").status_code == 204
    assert client.get("/api/tracker/periods", headers={"X-Unlock-Token": token}).status_code == 423

    # Unlock again with a real assertion
    opts = client.post("/api/auth/biometric/authenticate/options", headers=H)
    assert opts.status_code == 200
    options = opts.json()
    assert options["userVerification"] == "required"
    assert options["allowCredentials"][0]["id"] == b64url(authenticator.credential_id)
    res = client.post("/api/auth/biometric/authenticate/verify", json={"credential": authenticator.get(options)}, headers=H)
    assert res.status_code == 200, res.text
    new_token = res.json()["unlock_token"]
    assert client.get("/api/tracker/periods", headers={"X-Unlock-Token": new_token}).status_code == 200

    # Disabling requires a live unlock, then removes the credential and the gate
    assert client.delete("/api/auth/biometric").status_code == 423
    disabled = client.delete("/api/auth/biometric", headers={"X-Unlock-Token": new_token})
    assert disabled.status_code == 200 and disabled.json() == {"credentials_removed": 1}
    assert client.get("/api/auth/biometric/status").json()["enabled"] is False
    assert client.get("/api/tracker/periods").status_code == 200


def test_bad_assertions_are_rejected(client):
    authenticator = SoftwareAuthenticator()
    _enable(client, authenticator)
    client.post("/api/auth/biometric/lock")

    # Tampered signature
    options = client.post("/api/auth/biometric/authenticate/options", headers=H).json()
    res = client.post(
        "/api/auth/biometric/authenticate/verify",
        json={"credential": authenticator.get(options, tamper=True)},
        headers=H,
    )
    assert res.status_code == 401

    # Challenge replay: the same options cannot be used twice
    options = client.post("/api/auth/biometric/authenticate/options", headers=H).json()
    assertion = authenticator.get(options)
    assert client.post("/api/auth/biometric/authenticate/verify", json={"credential": assertion}, headers=H).status_code == 200
    assert client.post("/api/auth/biometric/authenticate/verify", json={"credential": assertion}, headers=H).status_code == 401

    # No user verification (e.g. a passcode-less tap) is not enough
    options = client.post("/api/auth/biometric/authenticate/options", headers=H).json()
    res = client.post(
        "/api/auth/biometric/authenticate/verify",
        json={"credential": authenticator.get(options, user_verified=False)},
        headers=H,
    )
    assert res.status_code == 401

    # A different device that was never registered
    stranger = SoftwareAuthenticator()
    options = client.post("/api/auth/biometric/authenticate/options", headers=H).json()
    res = client.post("/api/auth/biometric/authenticate/verify", json={"credential": stranger.get(options)}, headers=H)
    assert res.status_code == 401

    # Still locked after all of that
    assert client.get("/api/tracker/periods").status_code == 423


def test_registration_rejects_wrong_challenge_and_missing_uv(client):
    options = client.post("/api/auth/biometric/register/options", headers=H).json()
    authenticator = SoftwareAuthenticator()
    forged = dict(options, challenge=b64url(os.urandom(32)))
    res = client.post("/api/auth/biometric/register/verify", json={"credential": authenticator.create(forged)}, headers=H)
    assert res.status_code == 400
    assert client.get("/api/auth/biometric/status").json()["enabled"] is False

    options = client.post("/api/auth/biometric/register/options", headers=H).json()
    res = client.post(
        "/api/auth/biometric/register/verify",
        json={"credential": authenticator.create(options, user_verified=False)},
        headers=H,
    )
    assert res.status_code == 400
    assert client.get("/api/auth/biometric/status").json()["enabled"] is False


def test_lock_is_per_user(client, second_user):
    authenticator = SoftwareAuthenticator()
    _enable(client, authenticator)
    client.post("/api/auth/biometric/lock")
    # The other account is unaffected by my lock.
    other = {"X-User-Id": second_user}
    assert client.get("/api/tracker/periods", headers=other).status_code == 200
    assert client.get("/api/auth/biometric/status", headers=other).json()["enabled"] is False


def test_period_overlap_still_enforced_with_lock_off(client):
    """Regression guard: dependency refactor must not change tracker behaviour."""
    start = (date.today() - timedelta(days=10)).isoformat()
    assert client.post("/api/tracker/periods", json={"start_date": start}).status_code == 201
    assert client.post("/api/tracker/periods", json={"start_date": start}).status_code == 409
