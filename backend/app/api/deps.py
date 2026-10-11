from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import models
from app.db.init_db import LOCAL_USER_ID
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> models.User:
    """Resolve the acting user.

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


CurrentUser = Annotated[models.User, Depends(get_current_user)]
