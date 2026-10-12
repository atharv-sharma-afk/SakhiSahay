from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import models
from app.db.init_db import LOCAL_USER_ID
from app.db.session import get_db
from app.services import biometric_service

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_identity(
    db: DbSession,
    settings: AppSettings,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> models.User:
    """Resolve *who* is acting, without checking the app lock.

    MVP (AUTH_MODE=local): a single seeded local user. The optional X-User-Id
    header exists only so tests can prove per-user isolation of health records;
    it is not an authentication mechanism and is rejected outside local mode.
    JWT-based authentication replaces this dependency in Phase 2 without
    touching the route handlers.
    """
    if settings.auth_mode != "local":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Authentication mode not available yet")

    user_id = x_user_id or LOCAL_USER_ID
    user = db.scalar(select(models.User).where(models.User.id == user_id))
    if user is None:
        if user_id == LOCAL_USER_ID:
            user = models.User(id=LOCAL_USER_ID)
            db.add(user)
            db.commit()
        else:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown user")
    return user


Identity = Annotated[models.User, Depends(get_identity)]


def get_current_user(
    user: Identity,
    x_unlock_token: Annotated[str | None, Header(alias="X-Unlock-Token")] = None,
) -> models.User:
    """Identity *plus* the app-lock gate.

    When the user has enabled the biometric lock, every route that exposes or
    mutates health data requires a live unlock token obtained through a
    server-verified WebAuthn assertion. 423 tells the UI to show the lock screen.
    """
    if not biometric_service.is_unlocked(user, x_unlock_token):
        raise HTTPException(
            status.HTTP_423_LOCKED,
            "SakhiSahay is locked. Unlock with your device to continue.",
            headers={"X-App-Locked": "1"},
        )
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
