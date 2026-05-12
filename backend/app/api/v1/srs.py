"""SRS endpoints: rate cards, list due entries, get stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import DueEntry, MasterySnapshotResponse, RateRequest, StatsResponse
from app.services.quiz_service import get_quiz_by_key
from app.services.srs_service import get_due_count, rate_entry, select_due_entries


router = APIRouter(prefix="/srs", tags=["srs"])


@router.post(
    "/rate",
    response_model=MasterySnapshotResponse,
    summary="Submit an FSRS rating for one vocabulary entry.",
)
def post_rate(
    payload: RateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MasterySnapshotResponse:
    try:
        snapshot = rate_entry(
            db, user_id=user.id, entry_id=payload.entry_id, rating=payload.rating
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MasterySnapshotResponse.model_validate(snapshot)


@router.get(
    "/due",
    response_model=list[DueEntry],
    summary="Return the next entries to study, prioritized by FSRS due date.",
)
def get_due(
    quiz: str = Query(..., description="Quiz key, e.g. HSK1."),
    count: int = Query(10, ge=1, le=100),
    new_ratio: float = Query(0.30, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DueEntry]:
    if get_quiz_by_key(db, quiz) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz}' introuvable.",
        )
    entries = select_due_entries(
        db, user_id=user.id, quiz_key=quiz, count=count, new_ratio=new_ratio
    )
    return [DueEntry.model_validate(e) for e in entries]


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Counts of due / new / upcoming cards (optionally scoped to one quiz).",
)
def get_stats(
    quiz: str | None = Query(None, description="Optional quiz key to scope the stats."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsResponse:
    summary = get_due_count(db, user_id=user.id, quiz_key=quiz)
    return StatsResponse(**summary)
