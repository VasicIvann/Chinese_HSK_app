"""Expression écrite endpoints: subjects, generation, SSE-streamed correction, history."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import DAILY_QUOTAS, enforce_quota, get_current_user
from app.db.session import SessionLocal, get_db
from app.models import User
from app.schemas import (
    CorrectRequest,
    ExpressionAttemptItem,
    QuotaResponse,
    QuotaStatus,
    SubjectGenerateRequest,
    SubjectGenerateResponse,
    SubjectItem,
)
from app.services import expression_service, llm_service, subject_service
from app.services.srs_service import queue_entries_for_relearn


router = APIRouter(prefix="/expression", tags=["expression"])


@router.get(
    "/subjects",
    response_model=list[SubjectItem],
    summary="Return the curated subject pool, optionally scoped to one HSK level.",
)
def get_subjects(
    level: int | None = Query(None, ge=1, le=6),
    _user: User = Depends(get_current_user),
) -> list[SubjectItem]:
    return [SubjectItem(**item) for item in subject_service.list_subjects(level)]


@router.post(
    "/subjects/generate",
    response_model=SubjectGenerateResponse,
    summary="Generate a fresh writing subject via Claude for the given HSK level.",
)
def post_generate_subject(
    payload: SubjectGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(enforce_quota("subject_generation")),
) -> SubjectGenerateResponse:
    if not llm_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API Anthropic non configurée côté serveur.",
        )

    try:
        result, usage = llm_service.generate_subject(level=payload.level, theme=payload.theme)
    except llm_service.LLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    subject_text = str(result.get("subject", "")).strip()
    keywords = [str(k) for k in result.get("keywords", []) if str(k).strip()]
    if not subject_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Le modèle n'a pas renvoyé de sujet exploitable.",
        )

    updated = expression_service.increment_daily_usage(
        db,
        user_id=user.id,
        kind="subject_generation",
        count_delta=1,
        tokens_input_delta=usage.input_tokens,
        tokens_output_delta=usage.output_tokens,
    )

    return SubjectGenerateResponse(
        subject=subject_text,
        keywords=keywords,
        quota_remaining=max(0, DAILY_QUOTAS["subject_generation"] - int(updated.count or 0)),
    )


@router.get(
    "/attempts",
    response_model=list[ExpressionAttemptItem],
    summary="List the most recent expression attempts for the authenticated user.",
)
def list_attempts(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExpressionAttemptItem]:
    rows = expression_service.list_attempts(db, user_id=user.id, limit=limit)
    return [ExpressionAttemptItem(**row) for row in rows]


@router.get(
    "/quota",
    response_model=QuotaResponse,
    summary="Return today's quota usage for the authenticated user.",
)
def get_quota(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuotaResponse:
    correction_limit = DAILY_QUOTAS["expression_correction"]
    generation_limit = DAILY_QUOTAS["subject_generation"]

    correction_usage = expression_service.get_daily_usage(db, user.id, "expression_correction")
    generation_usage = expression_service.get_daily_usage(db, user.id, "subject_generation")

    return QuotaResponse(
        correction=QuotaStatus(
            kind="expression_correction",
            count=int(correction_usage.count or 0),
            limit=correction_limit,
            remaining=max(0, correction_limit - int(correction_usage.count or 0)),
        ),
        subject_generation=QuotaStatus(
            kind="subject_generation",
            count=int(generation_usage.count or 0),
            limit=generation_limit,
            remaining=max(0, generation_limit - int(generation_usage.count or 0)),
        ),
    )


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def _stream_correction_response(
    *, user_id: int, level: int, subject: str, user_text: str
) -> Iterator[bytes]:
    """SSE generator. Opens its own DB session to outlive the request scope.

    Emits typed events in order: start, partial*, complete, persisted (or error).
    """
    db: Session = SessionLocal()
    try:
        # Race-safe re-check: the dependency already gated on quota but this
        # protects against concurrent requests slipping past the same window.
        usage = expression_service.get_daily_usage(db, user_id, "expression_correction")
        if int(usage.count or 0) >= DAILY_QUOTAS["expression_correction"]:
            yield _sse("error", {"message": "Quota quotidien atteint."})
            db.commit()
            return

        accumulated_input = 0
        accumulated_output = 0
        correction: dict | None = None
        had_error = False

        for event in llm_service.stream_correction(user_text, level=level, subject=subject):
            yield _sse(event.type, event.data)
            if event.type == "error":
                had_error = True
                break
            if event.type == "complete":
                correction = event.data.get("correction", {})
                usage_payload = event.data.get("usage", {}) or {}
                accumulated_input = int(usage_payload.get("input_tokens", 0) or 0)
                accumulated_output = int(usage_payload.get("output_tokens", 0) or 0)

        if had_error or correction is None:
            db.commit()
            return

        score = correction.get("score")
        try:
            score_int = int(score) if score is not None else None
        except (TypeError, ValueError):
            score_int = None

        attempt = expression_service.record_attempt(
            db,
            user_id=user_id,
            hsk_level=level,
            subject=subject,
            user_text=user_text,
            correction=correction,
            score=score_int,
            tokens_input=accumulated_input,
            tokens_output=accumulated_output,
            model_id=llm_service.get_model_id(),
        )

        expression_service.increment_daily_usage(
            db,
            user_id=user_id,
            kind="expression_correction",
            count_delta=1,
            tokens_input_delta=accumulated_input,
            tokens_output_delta=accumulated_output,
        )

        mistakes = [
            str(m).strip()
            for m in correction.get("vocabulary_mistakes", [])
            if str(m).strip()
        ]
        mapping = expression_service.find_entry_ids_by_hanzi(db, mistakes)
        entry_ids = list({eid for eid in mapping.values() if eid})
        relearned = queue_entries_for_relearn(db, user_id, entry_ids) if entry_ids else 0

        db.commit()

        yield _sse(
            "persisted",
            {"attempt_id": attempt.id, "relearned_count": relearned},
        )
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        yield _sse("error", {"message": f"Erreur serveur: {exc}"})
    finally:
        db.close()


@router.post(
    "/correct",
    summary="Stream Claude's correction via SSE.",
    description=(
        "Returns a text/event-stream response with the following event sequence:\n\n"
        "- `start`: `{model}` — emitted before the first token.\n"
        "- `partial`: `{delta}` — emitted for each Claude text chunk.\n"
        "- `complete`: `{correction, usage}` — emitted once with the parsed JSON correction.\n"
        "- `persisted`: `{attempt_id, relearned_count}` — emitted after DB write + SRS re-queue.\n"
        "- `error`: `{message}` — emitted on failure; no further events follow."
    ),
    responses={
        200: {
            "description": "SSE stream",
            "content": {"text/event-stream": {"example": "event: start\ndata: {...}\n\n"}},
        }
    },
)
def post_correct(
    payload: CorrectRequest,
    user: User = Depends(enforce_quota("expression_correction")),
) -> StreamingResponse:
    if not llm_service.contains_chinese(payload.user_text):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le texte doit contenir des caractères chinois.",
        )
    if not llm_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API Anthropic non configurée côté serveur.",
        )

    return StreamingResponse(
        _stream_correction_response(
            user_id=user.id,
            level=payload.level,
            subject=payload.subject,
            user_text=payload.user_text,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
