"""Mastery dashboard endpoint: list per-entry mastery records for the user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Entry, Quiz, User, UserVocabMastery
from app.schemas import MasteryItem


router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.get(
    "",
    response_model=list[MasteryItem],
    summary="List mastery records for the authenticated user, optionally per quiz.",
)
def list_mastery(
    quiz: str | None = Query(None, description="Optional quiz key filter."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MasteryItem]:
    stmt = (
        select(UserVocabMastery, Entry, Quiz)
        .join(Entry, UserVocabMastery.entry_id == Entry.id)
        .join(Quiz, Entry.quiz_id == Quiz.id)
        .where(UserVocabMastery.user_id == user.id)
        .order_by(Quiz.level.asc(), Quiz.title.asc(), Entry.id.asc())
    )
    if quiz:
        stmt = stmt.where(Quiz.key == quiz)

    rows = db.execute(stmt).all()
    return [
        MasteryItem(
            quiz_key=quiz_row.key,
            quiz_title=quiz_row.title,
            entry_id=entry_row.id,
            hanzi=entry_row.hanzi,
            pinyin=entry_row.pinyin,
            translation=entry_row.translation,
            status=mastery.status,
            confidence_score=float(mastery.confidence_score or 0.0),
            review_count=int(mastery.review_count or 0),
            last_seen_at=mastery.last_seen_at,
            next_review_at=mastery.fsrs_due_at,
            stability_days=mastery.fsrs_stability,
            last_rating=mastery.fsrs_last_rating,
        )
        for mastery, entry_row, quiz_row in rows
    ]
