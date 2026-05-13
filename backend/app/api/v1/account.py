"""Account dashboard endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.account import AccountOverview
from app.services.account_service import get_overview


router = APIRouter(prefix="/account", tags=["account"])


@router.get(
    "/overview",
    response_model=AccountOverview,
    summary="Aggregated metrics for the dashboard: profile, mastery distribution, heatmap, trends.",
)
def get_account_overview(
    heatmap_days: int = Query(90, ge=7, le=365),
    trend_days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountOverview:
    payload = get_overview(db, user, heatmap_days=heatmap_days, trend_days=trend_days)
    return AccountOverview.model_validate(payload)
