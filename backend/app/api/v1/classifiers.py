"""Classifiers (量词) of HSK 1-3: fiches, fill-in sentences, usage quizzes."""

from __future__ import annotations

import logging
import random
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DAILY_QUOTAS, enforce_quota, get_current_user
from app.api.v1.exercises import _llm_ready, _version
from app.db.session import get_db
from app.models import User
from app.services import classifier_service, exercise_service, expression_service, llm_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/classifiers", tags=["classifiers"])

Version = Literal["2.0", "3.0"]
GENERATED_PER_CALL = 10


class GenerateRequest(BaseModel):
    version: Version | None = None
    level: int = Field(ge=1, le=3)
    hanzi: str | None = Field(None, max_length=2)


@router.get("", summary="Classifiers of a level (cumulative), with their fiche.")
def get_classifiers(
    level: int = Query(..., ge=1, le=3),
    version: Version | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    version = _version(db, user, version)
    return {
        "version": version,
        "level": level,
        "classifiers": classifier_service.fiches(db, user.id, version, level),
        "sentences": len(classifier_service.sentence_pool(db, user.id, version, level)),
    }


@router.get("/quiz", summary="A practice set: fill-in sentences (mode=fill) or usage questions (mode=usage).")
def get_quiz(
    mode: Literal["fill", "usage"] = Query(...),
    level: int = Query(..., ge=1, le=3),
    version: Version | None = Query(None),
    hanzi: str | None = Query(None, max_length=2),
    count: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    version = _version(db, user, version)
    if hanzi and hanzi not in classifier_service.by_hanzi(version, level):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Classificateur hors du niveau : {hanzi}.")
    if mode == "fill":
        questions = classifier_service.fill_quiz(db, user.id, version, level, count=count, hanzi=hanzi)
    else:
        questions = classifier_service.usage_quiz(version, level, count=count)
    return {"mode": mode, "version": version, "level": level, "hanzi": hanzi, "questions": questions}


@router.post("/generate", summary="Ask Claude for new fill-in sentences (kept for the user).")
def post_generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(enforce_quota("exercise_generation")),
) -> dict[str, Any]:
    version = _version(db, user, payload.version)
    known = classifier_service.by_hanzi(version, payload.level)
    if payload.hanzi and payload.hanzi not in known:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Classificateur hors du niveau : {payload.hanzi}.")
    _llm_ready()
    try:
        raw_items, usage = llm_service.generate_classifier_sentences(
            version=version,
            level=payload.level,
            classifiers=[(hz, c["usage"]) for hz, c in known.items()],
            focus=payload.hanzi,
            count=GENERATED_PER_CALL,
            vocabulary=list(exercise_service.vocabulary(version, payload.level)),
            avoid=classifier_service.existing_sentences(db, user.id, version, payload.level),
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    seen = set(classifier_service.existing_sentences(db, user.id, version, payload.level, limit=10_000))
    valid = []
    for raw in raw_items[:GENERATED_PER_CALL]:
        item = classifier_service.validate_generated(raw, version, payload.level)
        if item is None or (payload.hanzi and item["answer"] != payload.hanzi):
            log.info("generated classifier sentence dropped: %s", raw)
            continue
        plain = classifier_service.BLANK.sub(r"\1", item["zh"])
        if plain in seen:
            continue
        seen.add(plain)
        valid.append(item)
    if not valid:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Les phrases générées n'étaient pas utilisables. Réessaie.")

    saved = classifier_service.save_generated(
        db, user_id=user.id, version=version, level=payload.level, items=valid, model_id=llm_service.get_model_id()
    )
    updated = expression_service.increment_daily_usage(
        db,
        user_id=user.id,
        kind="exercise_generation",
        count_delta=1,
        tokens_input_delta=usage.input_tokens,
        tokens_output_delta=usage.output_tokens,
    )
    rng = random.Random()
    return {
        "mode": "fill",
        "version": version,
        "level": payload.level,
        "hanzi": payload.hanzi,
        "questions": [classifier_service.fill_question(s, version, payload.level, rng) for s in saved],
        "quota_remaining": max(0, DAILY_QUOTAS["exercise_generation"] - int(updated.count or 0)),
    }
