"""Quiz catalog endpoints: list quizzes and fetch entries for a quiz."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import EntryPublic, QuizPublic
from app.services.quiz_service import get_quiz_by_key, list_entries, list_quizzes
from app.services.version_service import HSK_VERSIONS, get_user_version


router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.get(
    "",
    response_model=list[QuizPublic],
    summary="List the quizzes (HSK levels) of a version — the user's chosen one by default.",
)
def get_quizzes(
    version: str | None = Query(None, description='"2.0", "3.0" or "all". Default: the user\'s version.'),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[QuizPublic]:
    if version is None:
        version = get_user_version(db, user.id)
    elif version != "all" and version not in HSK_VERSIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Version HSK inconnue.")
    quizzes = list_quizzes(db, None if version == "all" else version)
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
