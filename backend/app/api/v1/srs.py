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
from app.services.version_service import get_user_version


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
            db,
            user_id=user.id,
            entry_id=payload.entry_id,
            rating=payload.rating,
            record_log=True,
            mode=payload.mode,
            # Cap at 10 min: a card left open while away is not study time.
            elapsed_ms=min(payload.elapsed_ms, 600_000) if payload.elapsed_ms is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MasterySnapshotResponse.model_validate(snapshot)


MAX_SESSION_SIZE = 4000  # HSK 3.0 levels 1-5 = 3,600 words (2.0: 2,496)


def _quiz_keys_or_404(db: Session, raw: list[str]) -> list[str]:
    """Accept `?quiz=HSK2&quiz=HSK3` and/or `?quiz=HSK2,HSK3`; 404 on any unknown key."""
    keys: list[str] = []
    for item in raw:
        for key in item.split(","):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
    missing = [k for k in keys if get_quiz_by_key(db, k) is None]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz introuvable : {', '.join(missing)}.",
        )
    return keys


@router.get(
    "/due",
    response_model=list[DueEntry],
    summary="Return the next entries to study across one or more quizzes.",
)
def get_due(
    quiz: list[str] = Query(
        ..., description="One or more quiz keys: repeat the param or comma-separate (HSK2,HSK3)."
    ),
    count: int = Query(10, ge=1, le=MAX_SESSION_SIZE),
    new_ratio: float = Query(0.30, ge=0.0, le=1.0),
    only_new: bool = Query(False, description="Only words the user has never rated."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DueEntry]:
    keys = _quiz_keys_or_404(db, quiz)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sélectionne au moins un quiz.",
        )
    picked = select_due_entries(
        db,
        user_id=user.id,
        quiz_keys=keys,
        count=count,
        new_ratio=new_ratio,
        only_new=only_new,
    )
    # quiz_id = the level the word was picked from (a word can sit in a 2.0 and a 3.0 quiz).
    return [DueEntry.model_validate(e).model_copy(update={"quiz_id": quiz_id}) for e, quiz_id in picked]


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Counts of due / new / upcoming cards (some quizzes, or all of the user's HSK version).",
)
def get_stats(
    quiz: list[str] | None = Query(
        None, description="Optional quiz keys to scope the stats (repeat or comma-separate)."
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsResponse:
    keys = _quiz_keys_or_404(db, quiz) if quiz else None
    summary = get_due_count(db, user_id=user.id, quiz_keys=keys, version=get_user_version(db, user.id))
    return StatsResponse(**summary)
