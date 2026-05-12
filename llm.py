"""Anthropic Claude integration for the Expression écrite page.

Two operations:
- `generate_subject`: produce a fresh writing topic adapted to an HSK level.
- `correct_expression`: grade a user's Chinese production and return a
  structured JSON correction with errors, a corrected version, a score, and a
  list of HSK vocabulary that was used incorrectly (used to feed the SRS
  re-learning queue).

The system prompts are wrapped in `cache_control={"type": "ephemeral"}` blocks
so repeated calls within ~5 minutes pay only the cheap cache-read price.

API key resolution order:
1. `ANTHROPIC_API_KEY` environment variable
2. `st.secrets["ANTHROPIC_API_KEY"]` (Streamlit Cloud)

Model: defaults to `claude-haiku-4-5-20251001`. Override via the
`HSK_CLAUDE_MODEL` env var or `st.secrets["HSK_CLAUDE_MODEL"]`.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic, APIError


DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Approximate sentence-count guidance shown to Claude per HSK level.
LEVEL_LENGTH_GUIDANCE: Dict[int, str] = {
    1: "1 à 2 phrases courtes (10 à 30 caractères chinois au total).",
    2: "2 à 4 phrases (30 à 70 caractères chinois au total).",
    3: "4 à 7 phrases formant un petit paragraphe (70 à 150 caractères chinois).",
}

# Hard upper bounds enforced server-side before calling the LLM.
LEVEL_MAX_CHARS: Dict[int, int] = {1: 200, 2: 400, 3: 700}


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


class LLMQuotaError(RuntimeError):
    """Raised when the daily user quota would be exceeded."""


def _get_secret(name: str) -> Optional[str]:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st  # type: ignore

        secret = str(st.secrets.get(name, "")).strip()
        if secret:
            return secret
    except Exception:
        return None
    return None


def get_model_id() -> str:
    return _get_secret("HSK_CLAUDE_MODEL") or DEFAULT_MODEL


def _get_client() -> Anthropic:
    api_key = _get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMNotConfiguredError(
            "Aucune clé API Anthropic configurée. Ajoutez ANTHROPIC_API_KEY "
            "dans les secrets Streamlit ou en variable d'environnement."
        )
    return Anthropic(api_key=api_key)


def is_configured() -> bool:
    return bool(_get_secret("ANTHROPIC_API_KEY"))


def contains_chinese(text: str) -> bool:
    return bool(_HANZI_RE.search(text or ""))


def enforce_length(text: str, level: int) -> str:
    """Truncate the user submission to the level's max-chars guardrail."""
    limit = LEVEL_MAX_CHARS.get(level, 700)
    if len(text) <= limit:
        return text
    return text[:limit]


def _extract_json(raw: str) -> Dict[str, object]:
    """Parse a JSON object from the model output, even if it wraps the JSON."""
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


def generate_subject(level: int, theme: Optional[str] = None) -> Tuple[Dict[str, object], Dict[str, int]]:
    """Ask Claude for one fresh writing subject adapted to the HSK level.

    Returns `(payload, usage)` where `payload` has keys `subject` and `keywords`,
    and `usage` exposes `input_tokens` and `output_tokens` for quota tracking.
    """
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

    usage = {
        "input_tokens": int(getattr(message.usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(message.usage, "output_tokens", 0) or 0),
    }
    return payload, usage


def correct_expression(
    user_text: str,
    *,
    level: int,
    subject: str,
) -> Tuple[Dict[str, object], Dict[str, int]]:
    """Send the user's production to Claude and parse the structured grading."""
    client = _get_client()
    trimmed = enforce_length(user_text, level)
    length_hint = LEVEL_LENGTH_GUIDANCE.get(level, LEVEL_LENGTH_GUIDANCE[3])

    user_payload = (
        f"Niveau HSK : {level}\n"
        f"Longueur attendue : {length_hint}\n"
        f"Sujet imposé : {subject}\n\n"
        f"Production de l'apprenant :\n{trimmed}\n"
    )

    try:
        message = client.messages.create(
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
        )
    except APIError as exc:
        raise RuntimeError(f"Anthropic API error: {exc}") from exc

    raw_text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )

    correction: Dict[str, object]
    try:
        correction = _extract_json(raw_text)
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
            "_raw": raw_text,
        }

    correction.setdefault("errors", [])
    correction.setdefault("vocabulary_mistakes", [])
    correction.setdefault("strengths", [])

    usage = {
        "input_tokens": int(getattr(message.usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(message.usage, "output_tokens", 0) or 0),
    }
    return correction, usage


__all__ = [
    "DEFAULT_MODEL",
    "LEVEL_LENGTH_GUIDANCE",
    "LEVEL_MAX_CHARS",
    "LLMNotConfiguredError",
    "LLMQuotaError",
    "contains_chinese",
    "correct_expression",
    "enforce_length",
    "generate_subject",
    "get_model_id",
    "is_configured",
]
