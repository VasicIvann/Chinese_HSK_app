"""Tiny in-memory Anthropic SDK stand-in used in tests.

Mirrors enough of the real `anthropic.Anthropic` surface that `llm_service`
works without hitting the network. Tests monkey-patch
`llm_service._get_client` to return an instance of `FakeAnthropic`.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeUsage:
    input_tokens: int = 50
    output_tokens: int = 30


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list[FakeTextBlock]
    usage: FakeUsage = field(default_factory=FakeUsage)


class FakeStream:
    """Sync stream context manager mimicking `Anthropic.messages.stream`."""

    def __init__(self, final_text: str, usage: FakeUsage | None = None) -> None:
        self._final_text = final_text
        self._usage = usage or FakeUsage()

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *exc_info) -> None:  # noqa: ANN001
        return None

    @property
    def text_stream(self):
        # Emit the response in 5-char chunks to mimic Claude's token cadence.
        chunk_size = 5
        text = self._final_text
        for start in range(0, len(text), chunk_size):
            yield text[start : start + chunk_size]

    def get_final_message(self) -> FakeMessage:
        return FakeMessage(content=[FakeTextBlock(text=self._final_text)], usage=self._usage)


class FakeMessages:
    def __init__(
        self,
        *,
        subject_response: dict[str, Any] | None = None,
        correction_response: dict[str, Any] | None = None,
        example_response: dict[str, Any] | None = None,
    ) -> None:
        self.example_response = example_response or {
            "sentence": "我爱我的家。",
            "pinyin": "wǒ ài wǒ de jiā.",
            "translation": "J'aime ma famille.",
            "meaning_in_sentence": "爱 exprime ici l'affection pour sa famille.",
            "general_meaning": "爱 signifie aimer ; très courant dès le HSK 1.",
            "decomposition": "爱 contient 心 (cœur), qui porte l'idée d'affection.",
        }
        self.subject_response = subject_response or {
            "subject": "Décrivez votre week-end idéal.",
            "keywords": ["周末", "去", "玩", "和"],
        }
        self.correction_response = correction_response or {
            "score": 80,
            "corrected_version": "我今天很开心。",
            "pinyin": "wǒ jīn tiān hěn kāi xīn.",
            "french_translation": "Je suis très content aujourd'hui.",
            "errors": [],
            "vocabulary_mistakes": [],
            "strengths": ["Phrase simple et correcte."],
            "next_step_advice": "Essayez d'allonger en 2 phrases.",
        }
        self.create_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeMessage:
        self.create_calls.append(kwargs)
        system_text = "".join(block.get("text", "") for block in kwargs.get("system", []))
        response = (
            self.example_response if "phrase d'exemple" in system_text else self.subject_response
        )
        text = json.dumps(response, ensure_ascii=False)
        return FakeMessage(content=[FakeTextBlock(text=text)])

    def stream(self, **kwargs: Any) -> FakeStream:
        self.stream_calls.append(kwargs)
        text = json.dumps(self.correction_response, ensure_ascii=False)
        return FakeStream(final_text=text)


class FakeAnthropic:
    def __init__(
        self,
        *,
        subject_response: dict[str, Any] | None = None,
        correction_response: dict[str, Any] | None = None,
        example_response: dict[str, Any] | None = None,
    ) -> None:
        self.messages = FakeMessages(
            subject_response=subject_response,
            correction_response=correction_response,
            example_response=example_response,
        )


__all__ = ["FakeAnthropic", "FakeMessage", "FakeMessages", "FakeStream", "FakeTextBlock", "FakeUsage"]
