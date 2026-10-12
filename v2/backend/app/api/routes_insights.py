from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.insights import InsightsResponse
from app.services import tracker_service
from app.services.insights_service import build_insights

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("", response_model=InsightsResponse)
def get_insights(db: DbSession, user: CurrentUser) -> InsightsResponse:
    periods = tracker_service.list_periods(db, user.id)
    symptoms = tracker_service.list_symptoms(db, user.id)
    return build_insights(periods, symptoms)
