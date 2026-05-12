"""Anthropic Claude integration for the Expression écrite endpoints.

Three operations:
- `generate_subject`: one-shot, returns parsed JSON {subject, keywords}
- `stream_correction`: yields incremental text deltas + a final parsed JSON
- `is_configured`: liveness check used by the route

System prompts are wrapped in `cache_control={"type": "ephemeral"}` so repeated
calls within ~5 minutes pay only the cheap cache-read price.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Optional

from anthropic import Anthropic, APIError

from app.core.config import get_settings


LEVEL_LENGTH_GUIDANCE: dict[int, str] = {
    1: "1 à 2 phrases courtes (10 à 30 caractères chinois au total).",
    2: "2 à 4 phrases (30 à 70 caractères chinois au total).",
    3: "4 à 7 phrases formant un petit paragraphe (70 à 150 caractères chinois).",
}

LEVEL_MAX_CHARS: dict[int, int] = {1: 200, 2: 400, 3: 700}


SUBJECT_SYSTEM_PROMPT = """Tu es un professeur de chinois mandarin expérimenté qui crée des sujets de production écrite pour des apprenants francophones préparant les examens HSK officiels.

Pour chaque demande, tu génères UN SEUL sujet d'expression écrite court, motivant, qui respecte ces règles :
- Le sujet est adapté au niveau HSK demandé (vocabulaire et grammaire de ce niveau uniquement).
- Le sujet est concret, ancré dans la vie quotidienne, pas abstrait.
- Le sujet est rédigé en français, suivi entre parenthèses d'une suggestion de mots-clés HSK utiles (3 à 5 mots).
- Tu ne donnes JAMAIS d'exemple de réponse — juste l'énoncé.
- Tu réponds uniquement en JSON valide au format strict : {"subject": "<énoncé>", "keywords": ["<mot1>", "<mot2>", ...]}
- N'ajoute AUCUN texte avant ou après le JSON."""


CORRECTION_SYSTEM_PROMPT = """Tu es un correcteur expert qui évalue des productions écrites en chinois mandarin pour des apprenants francophones préparant les examens HSK officiels.

Pour chaque copie, tu renvoies une analyse rigoureuse et bienveillante au format JSON STRICT (aucun texte hors JSON) :

{
  "score": <entier 0-100>,
  "corrected_version": "<la production réécrite en chinois correct, en gardant l'intention de l'apprenant>",
  "pinyin": "<pinyin de la version corrigée, avec tons en diacritiques>",
  "french_translation": "<traduction française fidèle de la version corrigée>",
  "errors": [
    {
      "type": "<grammaire | vocabulaire | tons | orthographe | structure>",
      "segment": "<segment exact problématique extrait du texte de l'apprenant>",
      "correction": "<segment corrigé>",
      "explanation": "<explication concise en français>"
    }
  ],
  "vocabulary_mistakes": ["<hanzi mal utilisé 1>", "<hanzi mal utilisé 2>"],
  "strengths": ["<point fort 1 en français>", "<point fort 2 en français>"],
  "next_step_advice": "<un conseil concret en français pour progresser>"
}

Règles essentielles :
- Adapte la sévérité au niveau HSK indiqué : ne pénalise PAS l'absence de vocabulaire hors-niveau.
- `vocabulary_mistakes` ne contient QUE des hanzi du niveau HSK indiqué que l'apprenant a clairement mal utilisés (sens, contexte, ou collocation incorrecte). Si aucun mot HSK n'est mal utilisé, retourne une liste vide.
- Si la production ne contient pas de chinois ou est hors sujet, donne un score bas et explique-le dans `next_step_advice`.
- Si la production est parfaite, errors est une liste vide et le score est proche de 100.
- Réponds UNIQUEMENT avec le JSON. Aucun commentaire, aucun balisage Markdown, aucun préfixe."""


_HANZI_RE = re.compile(r"[一-鿿]")


class LLMNotConfiguredError(RuntimeError):
    """Raised when no Anthropic API key is available."""


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class StreamEvent:
    """One event emitted by stream_correction(). Mirrors the SSE event types."""

    type: str  # "start" | "partial" | "complete" | "error"
    data: dict[str, Any]


def is_configured() -> bool:
    return bool(get_settings().ANTHROPIC_API_KEY.strip())


def get_model_id() -> str:
    return get_settings().HSK_CLAUDE_MODEL


def contains_chinese(text: str) -> bool:
    return bool(_HANZI_RE.search(text or ""))


def enforce_length(text: str, level: int) -> str:
    limit = LEVEL_MAX_CHARS.get(level, 700)
    if len(text) <= limit:
        return text
    return text[:limit]


def _get_client() -> Anthropic:
    api_key = get_settings().ANTHROPIC_API_KEY.strip()
    if not api_key:
        raise LLMNotConfiguredError(
            "Aucune clé API Anthropic configurée. Ajoutez ANTHROPIC_API_KEY dans l'environnement."
        )
    return Anthropic(api_key=api_key)


def _extract_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group(0))
        raise


def generate_subject(level: int, theme: Optional[str] = None) -> tuple[dict[str, Any], LLMUsage]:
    """Ask Claude for one fresh writing subject. Sync, single-message."""
    client = _get_client()
    user_msg = f"Niveau HSK : {level}."
    if theme:
        user_msg += f" Thème souhaité : {theme.strip()}."
    user_msg += " Génère un sujet adapté."

    try:
        message = client.messages.create(
            model=get_model_id(),
            max_tokens=300,
            system=[
                {
                    "type": "text",
                    "text": SUBJECT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        )
    except APIError as exc:
        raise RuntimeError(f"Anthropic API error: {exc}") from exc

    raw_text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        payload = _extract_json(raw_text)
    except json.JSONDecodeError:
        payload = {"subject": raw_text.strip(), "keywords": []}

    usage = LLMUsage(
        input_tokens=int(getattr(message.usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(message.usage, "output_tokens", 0) or 0),
    )
    return payload, usage


def stream_correction(
    user_text: str, *, level: int, subject: str
) -> Iterator[StreamEvent]:
    """Stream Claude's correction. Yields StreamEvent in order: start, partial*, complete | error.

    The caller is responsible for SSE serialization. This service is transport-agnostic.
    """
    client = _get_client()
    trimmed = enforce_length(user_text, level)
    length_hint = LEVEL_LENGTH_GUIDANCE.get(level, LEVEL_LENGTH_GUIDANCE[3])

    user_payload = (
        f"Niveau HSK : {level}\n"
        f"Longueur attendue : {length_hint}\n"
        f"Sujet imposé : {subject}\n\n"
        f"Production de l'apprenant :\n{trimmed}\n"
    )

    yield StreamEvent(type="start", data={"model": get_model_id()})

    accumulated_text = ""
    input_tokens = 0
    output_tokens = 0

    try:
        with client.messages.stream(
            model=get_model_id(),
            max_tokens=1200,
            system=[
                {
                    "type": "text",
                    "text": CORRECTION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_payload}],
        ) as stream:
            for delta in stream.text_stream:
                accumulated_text += delta
                yield StreamEvent(type="partial", data={"delta": delta})

            final = stream.get_final_message()
            input_tokens = int(getattr(final.usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(final.usage, "output_tokens", 0) or 0)
    except APIError as exc:
        yield StreamEvent(type="error", data={"message": str(exc)})
        return
    except Exception as exc:  # pragma: no cover
        yield StreamEvent(type="error", data={"message": f"Unexpected error: {exc}"})
        return

    try:
        correction = _extract_json(accumulated_text)
    except json.JSONDecodeError:
        correction = {
            "score": 0,
            "corrected_version": "",
            "pinyin": "",
            "french_translation": "",
            "errors": [],
            "vocabulary_mistakes": [],
            "strengths": [],
            "next_step_advice": (
                "La correction renvoyée par le modèle n'a pas pu être analysée. "
                "Réessayez la soumission."
            ),
            "_raw": accumulated_text,
        }

    correction.setdefault("errors", [])
    correction.setdefault("vocabulary_mistakes", [])
    correction.setdefault("strengths", [])

    yield StreamEvent(
        type="complete",
        data={
            "correction": correction,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        },
    )


__all__ = [
    "CORRECTION_SYSTEM_PROMPT",
    "LEVEL_LENGTH_GUIDANCE",
    "LEVEL_MAX_CHARS",
    "LLMNotConfiguredError",
    "LLMUsage",
    "StreamEvent",
    "SUBJECT_SYSTEM_PROMPT",
    "contains_chinese",
    "enforce_length",
    "generate_subject",
    "get_model_id",
    "is_configured",
    "stream_correction",
]
