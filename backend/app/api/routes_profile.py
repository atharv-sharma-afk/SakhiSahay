from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(user: CurrentUser) -> ProfileOut:
    return ProfileOut.model_validate(user)


@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, db: DbSession, user: CurrentUser) -> ProfileOut:
    data = payload.model_dump(exclude_unset=True)
    completed = data.pop("onboarding_completed", None)
    if "goals" in data and data["goals"] is not None:
        data["goals"] = json.dumps(data["goals"])
    for key, value in data.items():
        setattr(user, key, value)
    if completed is True and user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(timezone.utc)
    elif completed is False:
        user.onboarding_completed_at = None
    db.commit()
    db.refresh(user)
    return ProfileOut.model_validate(user)
