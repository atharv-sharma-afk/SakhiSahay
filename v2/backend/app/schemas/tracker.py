from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

FlowLevel = Literal["spotting", "light", "medium", "heavy"]

# Configurable catalogue used by the API and the UI. These are tracking labels,
# not diagnostic indicators. "mood" entries include neutral/positive states so a
# daily check-in can be recorded without forcing everything to be a "symptom".
SYMPTOM_CATALOGUE: list[dict[str, str]] = [
    {"key": "cramps", "label": "Cramps", "group": "pain"},
    {"key": "back_pain", "label": "Back pain", "group": "pain"},
    {"key": "headache", "label": "Headache", "group": "pain"},
    {"key": "breast_tenderness", "label": "Breast tenderness", "group": "pain"},
    {"key": "bloating", "label": "Bloating", "group": "body"},
    {"key": "fatigue", "label": "Fatigue", "group": "body"},
    {"key": "nausea", "label": "Nausea", "group": "body"},
    {"key": "acne", "label": "Acne", "group": "body"},
    {"key": "cravings", "label": "Cravings", "group": "body"},
    {"key": "spotting", "label": "Spotting", "group": "bleeding"},
    {"key": "heavy_bleeding", "label": "Heavy bleeding", "group": "bleeding"},
    {"key": "calm", "label": "Calm", "group": "mood"},
    {"key": "energetic", "label": "Energetic", "group": "mood"},
    {"key": "mood_changes", "label": "Mood swings", "group": "mood"},
    {"key": "irritable", "label": "Irritable", "group": "mood"},
    {"key": "anxiety", "label": "Anxious", "group": "mood"},
    {"key": "low_mood", "label": "Low mood", "group": "mood"},
    {"key": "sleep_changes", "label": "Sleep changes", "group": "mood"},
]
SYMPTOM_KEYS = {s["key"] for s in SYMPTOM_CATALOGUE}

MAX_NOTE_LENGTH = 500


def as_utc(value: datetime) -> datetime:
    """Timestamps are written as UTC; SQLite drops the offset on the way back.

    Re-attach UTC before serialising so clients receive an unambiguous instant
    (``...Z``) instead of a naive string they would misread as local time.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class TimestampedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_ts(self, value: datetime) -> str:
        return as_utc(value).isoformat().replace("+00:00", "Z")


def _reject_future(value: date, field_name: str) -> date:
    if value > date.today():
        raise ValueError(f"{field_name} cannot be in the future")
    return value


class PeriodBase(BaseModel):
    start_date: date
    end_date: date | None = None
    flow: FlowLevel | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)

    @field_validator("start_date")
    @classmethod
    def _start_not_future(cls, v: date) -> date:
        return _reject_future(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def _end_not_future(cls, v: date | None) -> date | None:
        return None if v is None else _reject_future(v, "end_date")

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None

    @model_validator(mode="after")
    def _check_range(self):
        if self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
            if (self.end_date - self.start_date).days > 30:
                raise ValueError("A single period record cannot span more than 31 days")
        return self


class PeriodCreate(PeriodBase):
    pass


class PeriodUpdate(PeriodBase):
    pass


class PeriodOut(PeriodBase, TimestampedOut):
    @property
    def duration_days(self) -> int | None:
        if self.end_date is None:
            return None
        return (self.end_date - self.start_date).days + 1


class SymptomBase(BaseModel):
    record_date: date
    symptom: str
    severity: int | None = Field(default=None, ge=1, le=3)
    notes: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)

    @field_validator("record_date")
    @classmethod
    def _date_not_future(cls, v: date) -> date:
        return _reject_future(v, "record_date")

    @field_validator("symptom")
    @classmethod
    def _known_symptom(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SYMPTOM_KEYS:
            raise ValueError(f"Unknown symptom '{v}'. Use one of the catalogue keys.")
        return v

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class SymptomCreate(SymptomBase):
    pass


class SymptomUpdate(SymptomBase):
    pass


class SymptomOut(SymptomBase, TimestampedOut):
    pass


class SymptomCatalogueItem(BaseModel):
    key: str
    label: str
    group: str


class TrackerSummary(BaseModel):
    period_count: int
    symptom_count: int
    first_record_date: date | None
    last_period_start: date | None
    current_period_open: bool
