from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.tracker import (
    PeriodCreate,
    PeriodUpdate,
    SymptomCreate,
    SymptomUpdate,
    TrackerSummary,
)


class OverlapError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


# ---------------------------------------------------------------- periods


def list_periods(db: Session, user_id: str) -> list[models.PeriodRecord]:
    stmt = (
        select(models.PeriodRecord)
        .where(models.PeriodRecord.user_id == user_id)
        .order_by(models.PeriodRecord.start_date.desc())
    )
    return list(db.scalars(stmt))


def _assert_no_overlap(
    db: Session, user_id: str, start: date, end: date | None, exclude_id: str | None = None
) -> None:
    """Two period records for the same user may not overlap.

    An open record (no end date) is treated as covering only its start day for
    overlap purposes, so a user can close it later without being blocked.
    """
    effective_end = end or start
    for existing in list_periods(db, user_id):
        if existing.id == exclude_id:
            continue
        ex_end = existing.end_date or existing.start_date
        if start <= ex_end and existing.start_date <= effective_end:
            raise OverlapError(
                f"Overlaps with the period starting {existing.start_date.isoformat()}"
            )


def create_period(db: Session, user_id: str, data: PeriodCreate) -> models.PeriodRecord:
    _assert_no_overlap(db, user_id, data.start_date, data.end_date)
    record = models.PeriodRecord(user_id=user_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_period(db: Session, user_id: str, period_id: str) -> models.PeriodRecord:
    record = db.get(models.PeriodRecord, period_id)
    if record is None or record.user_id != user_id:
        raise NotFoundError("Period record not found")
    return record


def update_period(db: Session, user_id: str, period_id: str, data: PeriodUpdate) -> models.PeriodRecord:
    record = get_period(db, user_id, period_id)
    _assert_no_overlap(db, user_id, data.start_date, data.end_date, exclude_id=record.id)
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_period(db: Session, user_id: str, period_id: str) -> None:
    record = get_period(db, user_id, period_id)
    db.delete(record)
    db.commit()


# ---------------------------------------------------------------- symptoms


def list_symptoms(
    db: Session, user_id: str, start: date | None = None, end: date | None = None
) -> list[models.SymptomRecord]:
    stmt = select(models.SymptomRecord).where(models.SymptomRecord.user_id == user_id)
    if start:
        stmt = stmt.where(models.SymptomRecord.record_date >= start)
    if end:
        stmt = stmt.where(models.SymptomRecord.record_date <= end)
    stmt = stmt.order_by(models.SymptomRecord.record_date.desc(), models.SymptomRecord.created_at.desc())
    return list(db.scalars(stmt))


def create_symptom(db: Session, user_id: str, data: SymptomCreate) -> models.SymptomRecord:
    record = models.SymptomRecord(user_id=user_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_symptom(db: Session, user_id: str, symptom_id: str) -> models.SymptomRecord:
    record = db.get(models.SymptomRecord, symptom_id)
    if record is None or record.user_id != user_id:
        raise NotFoundError("Symptom record not found")
    return record


def update_symptom(db: Session, user_id: str, symptom_id: str, data: SymptomUpdate) -> models.SymptomRecord:
    record = get_symptom(db, user_id, symptom_id)
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_symptom(db: Session, user_id: str, symptom_id: str) -> None:
    record = get_symptom(db, user_id, symptom_id)
    db.delete(record)
    db.commit()


# ---------------------------------------------------------------- summary


def summary(db: Session, user_id: str) -> TrackerSummary:
    periods = list_periods(db, user_id)
    symptom_count = db.scalar(
        select(func.count()).select_from(models.SymptomRecord).where(models.SymptomRecord.user_id == user_id)
    ) or 0
    first_symptom = db.scalar(
        select(func.min(models.SymptomRecord.record_date)).where(models.SymptomRecord.user_id == user_id)
    )
    first_period = min((p.start_date for p in periods), default=None)
    candidates = [d for d in (first_symptom, first_period) if d is not None]
    latest = periods[0] if periods else None
    return TrackerSummary(
        period_count=len(periods),
        symptom_count=int(symptom_count),
        first_record_date=min(candidates) if candidates else None,
        last_period_start=latest.start_date if latest else None,
        current_period_open=bool(latest and latest.end_date is None),
    )


def delete_all_user_data(db: Session, user_id: str) -> dict[str, int]:
    """Erase every health record for a user (data-deletion control)."""
    periods = list_periods(db, user_id)
    symptoms = list_symptoms(db, user_id)
    for record in [*periods, *symptoms]:
        db.delete(record)
    db.commit()
    return {"periods_deleted": len(periods), "symptoms_deleted": len(symptoms)}
