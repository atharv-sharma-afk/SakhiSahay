from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.tracker import as_utc

Language = Literal["en", "hi", "hinglish"]
YesNoUnsure = Literal["yes", "no", "unsure"]

# Onboarding choices are a fixed vocabulary so the UI can translate them and
# stored values stay meaningful across languages.
GOAL_KEYS = {
    "track_period",
    "understand_symptoms",
    "ask_questions",
    "doctor_visit",
    "healthy_habits",
    "learn_cycle",
}
FEELING_KEYS = {"love_hate", "embarrassed", "dislike", "want_to_understand", "friends"}

MIN_CYCLE, MAX_CYCLE = 15, 60
MIN_PERIOD, MAX_PERIOD = 1, 14


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    preferred_language: str
    age: int | None
    cycle_length_days: int
    period_length_days: int
    periods_regular: str | None
    period_feeling: str | None
    cycle_affects_sleep: str | None
    goals: list[str] = Field(default_factory=list)
    onboarding_completed_at: datetime | None
    biometric_lock_enabled: bool
    lock_timeout_seconds: int

    @field_validator("goals", mode="before")
    @classmethod
    def _parse_goals(cls, v):  # stored as a JSON string in SQLite
        if v is None or v == "":
            return []
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
            except ValueError:
                return []
            return [str(g) for g in parsed] if isinstance(parsed, list) else []
        return v

    @field_serializer("onboarding_completed_at")
    def _ser_completed(self, value: datetime | None) -> str | None:
        return None if value is None else as_utc(value).isoformat().replace("+00:00", "Z")


class ProfileUpdate(BaseModel):
    """Partial update: only the fields present in the request body are changed."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    preferred_language: Language | None = None
    age: int | None = Field(default=None, ge=10, le=80)
    cycle_length_days: int | None = Field(default=None, ge=MIN_CYCLE, le=MAX_CYCLE)
    period_length_days: int | None = Field(default=None, ge=MIN_PERIOD, le=MAX_PERIOD)
    periods_regular: YesNoUnsure | None = None
    period_feeling: str | None = None
    cycle_affects_sleep: YesNoUnsure | None = None
    goals: list[str] | None = None
    lock_timeout_seconds: int | None = Field(default=None, ge=0, le=3600)
    # Set to true by the final onboarding step; the server stamps the time.
    onboarding_completed: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        if not v:
            raise ValueError("Display name cannot be empty")
        return v

    @field_validator("period_feeling")
    @classmethod
    def _known_feeling(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in FEELING_KEYS:
            raise ValueError("Unknown period_feeling value")
        return v

    @field_validator("goals")
    @classmethod
    def _known_goals(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        unknown = [g for g in v if g not in GOAL_KEYS]
        if unknown:
            raise ValueError(f"Unknown goal(s): {', '.join(unknown)}")
        # de-duplicate while preserving order
        seen: set[str] = set()
        return [g for g in v if not (g in seen or seen.add(g))]
