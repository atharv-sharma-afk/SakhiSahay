from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.tracker import (
    SYMPTOM_CATALOGUE,
    PeriodCreate,
    PeriodOut,
    PeriodUpdate,
    SymptomCatalogueItem,
    SymptomCreate,
    SymptomOut,
    SymptomUpdate,
    TrackerSummary,
)
from app.services import tracker_service as svc

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.get("/summary", response_model=TrackerSummary)
def get_summary(db: DbSession, user: CurrentUser) -> TrackerSummary:
    return svc.summary(db, user.id)


@router.get("/symptom-catalogue", response_model=list[SymptomCatalogueItem])
def get_symptom_catalogue() -> list[dict[str, str]]:
    return SYMPTOM_CATALOGUE


# ---- periods ---------------------------------------------------------------


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(db: DbSession, user: CurrentUser):
    return svc.list_periods(db, user.id)


@router.post("/periods", response_model=PeriodOut, status_code=status.HTTP_201_CREATED)
def create_period(payload: PeriodCreate, db: DbSession, user: CurrentUser):
    try:
        return svc.create_period(db, user.id, payload)
    except svc.OverlapError as exc:
        raise _conflict(exc) from exc


@router.put("/periods/{period_id}", response_model=PeriodOut)
def update_period(period_id: str, payload: PeriodUpdate, db: DbSession, user: CurrentUser):
    try:
        return svc.update_period(db, user.id, period_id, payload)
    except svc.NotFoundError as exc:
        raise _not_found(exc) from exc
    except svc.OverlapError as exc:
        raise _conflict(exc) from exc


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(period_id: str, db: DbSession, user: CurrentUser):
    try:
        svc.delete_period(db, user.id, period_id)
    except svc.NotFoundError as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- symptoms --------------------------------------------------------------


@router.get("/symptoms", response_model=list[SymptomOut])
def list_symptoms(
    db: DbSession,
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
):
    return svc.list_symptoms(db, user.id, start, end)


@router.post("/symptoms", response_model=SymptomOut, status_code=status.HTTP_201_CREATED)
def create_symptom(payload: SymptomCreate, db: DbSession, user: CurrentUser):
    return svc.create_symptom(db, user.id, payload)


@router.put("/symptoms/{symptom_id}", response_model=SymptomOut)
def update_symptom(symptom_id: str, payload: SymptomUpdate, db: DbSession, user: CurrentUser):
    try:
        return svc.update_symptom(db, user.id, symptom_id, payload)
    except svc.NotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/symptoms/{symptom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom(symptom_id: str, db: DbSession, user: CurrentUser):
    try:
        svc.delete_symptom(db, user.id, symptom_id)
    except svc.NotFoundError as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- privacy controls --------------------------------------------------------


@router.delete("/all", status_code=status.HTTP_200_OK)
def delete_all(db: DbSession, user: CurrentUser) -> dict[str, int]:
    """Delete every period and symptom record belonging to the current user."""
    return svc.delete_all_user_data(db, user.id)
