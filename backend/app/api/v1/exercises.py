"""HSK-format practice: listening and writing parts of the papers, grammar points."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DAILY_QUOTAS, enforce_quota, get_current_user
from app.db.session import get_db
from app.models import User
from app.services import exercise_service, expression_service, grammar_service, llm_service
from app.services.exercise_schema import InvalidItem, normalize
from app.services.version_service import get_user_version

log = logging.getLogger(__name__)
router = APIRouter(tags=["exercises"])

Section = Literal["listening", "writing"]
Level = Literal[1, 2, 3]
Version = Literal["2.0", "3.0"]


def _version(db: Session, user: User, requested: str | None) -> str:
    """The version the page shows (sent by the client), else the user's saved one."""
    return requested if requested in ("2.0", "3.0") else get_user_version(db, user.id)


class Answer(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    correct: bool


class ResultRequest(BaseModel):
    section: Literal["listening", "writing", "grammar"]
    version: Version | None = None
    level: Level
    part: str = Field(min_length=1, max_length=32)
    answers: list[Answer] = Field(min_length=1, max_length=200)


class GenerateRequest(BaseModel):
    section: Section
    version: Version | None = None
    level: Level
    part: str = Field(min_length=1, max_length=8)


class SentenceCheckRequest(BaseModel):
    level: Level
    word: str = Field(min_length=1, max_length=16)
    sentence: str = Field(min_length=1, max_length=120)


def _llm_ready() -> None:
    if not llm_service.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API Anthropic non configurée côté serveur.")


@router.get("/exercises/catalog", summary="Parts of the paper (user's HSK version) with availability and scores.")
def get_catalog(
    section: Section = Query(...),
    level: int = Query(..., ge=1, le=3),
    version: Version | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    version = _version(db, user, version)
    return {
        "version": version,
        "level": level,
        "section": section,
        "parts": exercise_service.catalog(db, user.id, version, level, section),
    }


@router.get("/exercises/set", summary="A practice set for one part (or part=all for the whole section).")
def get_set(
    section: Section = Query(...),
    level: int = Query(..., ge=1, le=3),
    part: str = Query(..., max_length=8),
    version: Version | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    version = _version(db, user, version)
    try:
        return exercise_service.build_set(db, user.id, version, level, section, part)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Partie introuvable : {part}.") from None


@router.post("/exercises/results", status_code=status.HTTP_201_CREATED, summary="Save a finished set.")
def post_result(
    payload: ResultRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    row = exercise_service.save_result(
        db,
        user_id=user.id,
        version=_version(db, user, payload.version),
        level=payload.level,
        section=payload.section,
        part_key=payload.part,
        answers=[a.model_dump() for a in payload.answers],
    )
    return {"id": row.id, "score": row.score, "total": row.total}


@router.post("/exercises/generate", summary="Ask Claude for a brand-new set for one part.")
def post_generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(enforce_quota("exercise_generation")),
) -> dict[str, Any]:
    version = _version(db, user, payload.version)
    part = exercise_service.find_part(version, payload.level, payload.section, payload.part)
    if part is None or not exercise_service.part_slots(part):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partie introuvable.")
    _llm_ready()

    items: list[dict[str, Any]] = []
    tokens_in = tokens_out = 0
    for item_type, count in exercise_service.part_slots(part):
        wanted = max(1, count // exercise_service.GROUP_SIZE) if item_type in exercise_service.GROUP_TYPES else count
        existing = exercise_service.pool(db, user.id, version, payload.level, item_type)
        try:
            raw_items, usage = llm_service.generate_exercises(
                item_type=item_type,
                version=version,
                level=payload.level,
                count=wanted,
                vocabulary=list(exercise_service.vocabulary(version, payload.level)),
                avoid=exercise_service.recent_texts(existing),
            )
        except RuntimeError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        tokens_in += usage.input_tokens
        tokens_out += usage.output_tokens
        valid = []
        for raw in raw_items[:wanted]:
            try:
                item = normalize(raw, item_type, payload.level)
            except InvalidItem as exc:
                log.info("generated %s item dropped: %s", item_type, exc)
                continue
            # At most one character outside the level's lists (a name, a rare word).
            if len(exercise_service.unknown_chars(item, version, payload.level)) > 1:
                continue
            valid.append(item)
        items += exercise_service.save_generated(
            db,
            user_id=user.id,
            version=version,
            level=payload.level,
            item_type=item_type,
            items=valid,
            model_id=llm_service.get_model_id(),
        )
    if not items:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Les questions générées n'étaient pas utilisables. Réessaie.")

    updated = expression_service.increment_daily_usage(
        db,
        user_id=user.id,
        kind="exercise_generation",
        count_delta=1,
        tokens_input_delta=tokens_in,
        tokens_output_delta=tokens_out,
    )
    return {
        "version": version,
        "level": payload.level,
        "section": payload.section,
        "part": payload.part,
        "parts": [{**part, "items": items}],
        "quota_remaining": max(0, DAILY_QUOTAS["exercise_generation"] - int(updated.count or 0)),
    }


@router.post("/exercises/check-sentence", summary="Claude grades a sentence written with an imposed word.")
def post_check_sentence(
    payload: SentenceCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(enforce_quota("exercise_check")),
) -> dict[str, Any]:
    _llm_ready()
    try:
        result, usage = llm_service.check_sentence(
            word=payload.word, sentence=payload.sentence.strip(), level=payload.level
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    expression_service.increment_daily_usage(
        db,
        user_id=user.id,
        kind="exercise_check",
        count_delta=1,
        tokens_input_delta=usage.input_tokens,
        tokens_output_delta=usage.output_tokens,
    )
    return result


@router.get("/grammar", summary="Official grammar points of a level, with explanations and the user's progress.")
def get_grammar(
    level: int = Query(..., ge=1, le=3),
    version: Version | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "level": level,
        "version": _version(db, user, version),
        "points": grammar_service.points_with_progress(db, user.id, level),
    }
