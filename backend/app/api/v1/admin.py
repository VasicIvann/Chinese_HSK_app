"""Read-only Admin endpoints: counters about the registered accounts.

Reserved to the e-mails listed in ADMIN_EMAILS (checked on every request).
Nothing here changes data, and no content written by the users is returned.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.timezone import get_user_timezone
from app.db.session import get_db
from app.models import User
from app.schemas.account import StudyStats
from app.services.admin_service import users_overview
from app.services.stats_service import PERIODS, study_stats
from app.services.version_service import get_user_version

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", summary="Every account with its activity counters, plus site-wide figures.")
def get_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    tz: ZoneInfo = Depends(get_user_timezone),
) -> dict[str, Any]:
    return users_overview(db, tz=tz)


@router.get("/users/{user_id}/stats", summary="The study statistics of one account (same as its Account page).")
def get_user_stats(
    user_id: int,
    days: int = Query(30),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    tz: ZoneInfo = Depends(get_user_timezone),
) -> dict[str, Any]:
    if days not in PERIODS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Période possible : {', '.join(map(str, PERIODS))} jours.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")
    version = get_user_version(db, user.id)
    stats = StudyStats.model_validate(study_stats(db, user.id, version=version, days=days, tz=tz))
    return {
        "user": {"id": user.id, "email": user.email, "created_at": user.created_at, "hsk_version": version},
        "stats": stats.model_dump(mode="json"),
    }
