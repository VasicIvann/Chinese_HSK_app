"""Account dashboard endpoint."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.timezone import get_user_timezone
from app.db.session import get_db
from app.models import User
from app.schemas.account import AccountOverview, AccountSettings
from app.services.account_service import get_overview
from app.services.version_service import get_user_version, set_user_version


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
    tz: ZoneInfo = Depends(get_user_timezone),
) -> AccountOverview:
    payload = get_overview(
        db,
        user,
        heatmap_days=heatmap_days,
        trend_days=trend_days,
        tz=tz,
        version=get_user_version(db, user.id),
    )
    return AccountOverview.model_validate(payload)


@router.get("/settings", response_model=AccountSettings, summary="The user's study settings (HSK version).")
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountSettings:
    return AccountSettings(hsk_version=get_user_version(db, user.id))


@router.put(
    "/settings",
    response_model=AccountSettings,
    summary="Change the user's study settings. Switching HSK version keeps all progress.",
)
def put_settings(
    payload: AccountSettings,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountSettings:
    return AccountSettings(hsk_version=set_user_version(db, user.id, payload.hsk_version))
