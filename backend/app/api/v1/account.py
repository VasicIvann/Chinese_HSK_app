"""Account dashboard endpoint."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.timezone import get_user_timezone
from app.db.session import get_db
from app.models import User
from app.schemas.account import AccountOverview, AccountSettings, AccountSettingsUpdate, StudyStats
from app.services.account_service import get_overview
from app.services.stats_service import PERIODS, study_stats
from app.services.version_service import (
    get_pinyin_locked,
    get_user_version,
    set_pinyin_locked,
    set_user_version,
)


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


@router.get(
    "/stats",
    response_model=StudyStats,
    summary="Study statistics over 7, 30 or 90 days: activity per tab, vocabulary growth, time and habits.",
)
def get_account_stats(
    days: int = Query(30),
    version: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    tz: ZoneInfo = Depends(get_user_timezone),
) -> StudyStats:
    if days not in PERIODS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Période possible : {', '.join(map(str, PERIODS))} jours.")
    version = version if version in ("2.0", "3.0") else get_user_version(db, user.id)
    return StudyStats.model_validate(study_stats(db, user.id, version=version, days=days, tz=tz))


def _settings(db: Session, user_id: int) -> AccountSettings:
    return AccountSettings(hsk_version=get_user_version(db, user_id), pinyin_locked=get_pinyin_locked(db, user_id))


@router.get(
    "/settings",
    response_model=AccountSettings,
    summary="The user's study settings (HSK version, pinyin lock).",
)
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountSettings:
    return _settings(db, user.id)


@router.put(
    "/settings",
    response_model=AccountSettings,
    summary="Change the user's study settings (only the fields sent). Switching HSK version keeps all progress.",
)
def put_settings(
    payload: AccountSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountSettings:
    if payload.hsk_version is not None:
        set_user_version(db, user.id, payload.hsk_version)
    if payload.pinyin_locked is not None:
        set_pinyin_locked(db, user.id, payload.pinyin_locked)
    return _settings(db, user.id)
