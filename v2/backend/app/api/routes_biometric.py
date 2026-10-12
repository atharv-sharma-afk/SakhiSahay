"""App-lock routes. See ``app.services.biometric_service`` for the security model.

Routes use ``Identity`` (not ``CurrentUser``) because they are the way *out* of a
locked state; they expose no health data.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, DbSession, Identity
from app.services import biometric_service as svc

router = APIRouter(prefix="/api/auth/biometric", tags=["app-lock"])


class LockStatus(BaseModel):
    enabled: bool
    credential_count: int
    lock_timeout_seconds: int
    unlocked: bool
    rp_name: str


class CredentialPayload(BaseModel):
    credential: dict[str, Any]
    label: str | None = Field(default=None, max_length=80)


class UnlockResult(BaseModel):
    unlock_token: str
    expires_in_seconds: int


def _rp(request: Request, settings) -> tuple[str, str]:
    try:
        return svc.resolve_rp(request.headers.get("origin"), settings.webauthn_rp_id, settings.webauthn_origin_list)
    except svc.BiometricError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _ttl(settings) -> int:
    return settings.unlock_token_ttl_minutes * 60


@router.get("/status", response_model=LockStatus)
def lock_status(
    db: DbSession,
    user: Identity,
    settings: AppSettings,
    x_unlock_token: Annotated[str | None, Header(alias="X-Unlock-Token")] = None,
) -> LockStatus:
    return LockStatus(
        enabled=user.biometric_lock_enabled,
        credential_count=len(svc.list_credentials(db, user.id)),
        lock_timeout_seconds=user.lock_timeout_seconds,
        unlocked=svc.is_unlocked(user, x_unlock_token),
        rp_name=settings.webauthn_rp_name,
    )


@router.post("/register/options")
def register_options(request: Request, db: DbSession, user: Identity, settings: AppSettings) -> dict:
    rp_id, _ = _rp(request, settings)
    return svc.registration_options(db, user, rp_id, settings.webauthn_rp_name)


@router.post("/register/verify", response_model=UnlockResult, status_code=status.HTTP_201_CREATED)
def register_verify(
    payload: CredentialPayload, request: Request, db: DbSession, user: Identity, settings: AppSettings
) -> UnlockResult:
    rp_id, origin = _rp(request, settings)
    try:
        _, token = svc.complete_registration(
            db, user, payload.credential, rp_id, origin, payload.label, _ttl(settings)
        )
    except svc.BiometricError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return UnlockResult(unlock_token=token, expires_in_seconds=_ttl(settings))


@router.post("/authenticate/options")
def authenticate_options(request: Request, db: DbSession, user: Identity, settings: AppSettings) -> dict:
    rp_id, _ = _rp(request, settings)
    try:
        return svc.authentication_options(db, user, rp_id)
    except svc.BiometricError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/authenticate/verify", response_model=UnlockResult)
def authenticate_verify(
    payload: CredentialPayload, request: Request, db: DbSession, user: Identity, settings: AppSettings
) -> UnlockResult:
    rp_id, origin = _rp(request, settings)
    try:
        token = svc.complete_authentication(db, user, payload.credential, rp_id, origin, _ttl(settings))
    except svc.BiometricError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return UnlockResult(unlock_token=token, expires_in_seconds=_ttl(settings))


@router.post("/lock", status_code=status.HTTP_204_NO_CONTENT)
def lock_now(user: Identity) -> None:
    """Explicit lock: revoke every unlock token for this user."""
    svc.relock(user.id)


@router.delete("", status_code=status.HTTP_200_OK)
def disable(
    db: DbSession,
    user: Identity,
    x_unlock_token: Annotated[str | None, Header(alias="X-Unlock-Token")] = None,
) -> dict[str, int]:
    """Turn the lock off. Requires a *current* unlock (fresh device verification)."""
    if user.biometric_lock_enabled and not svc.is_unlocked(user, x_unlock_token):
        raise HTTPException(status.HTTP_423_LOCKED, "Verify with your device before turning the lock off")
    removed = svc.disable_lock(db, user)
    return {"credentials_removed": removed}
