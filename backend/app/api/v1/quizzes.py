"""Quiz catalog endpoints: list quizzes and fetch entries for a quiz."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import EntryPublic, QuizPublic
from app.services.quiz_service import get_quiz_by_key, list_entries, list_quizzes


router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.get(
    "",
    response_model=list[QuizPublic],
    summary="List every available quiz (HSK level, title).",
)
def get_quizzes(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[QuizPublic]:
    quizzes = list_quizzes(db)
    return [QuizPublic.model_validate(q) for q in quizzes]


@router.get(
    "/{quiz_key}/entries",
    response_model=list[EntryPublic],
    summary="List all vocabulary entries for the given quiz key (e.g., HSK1).",
)
def get_entries(
    quiz_key: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[EntryPublic]:
    quiz = get_quiz_by_key(db, quiz_key)
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_key}' introuvable.",
        )
    entries = list_entries(db, quiz_key)
    return [EntryPublic.model_validate(e) for e in entries]
