"""Tiny in-memory Anthropic SDK stand-in used in tests.

Mirrors enough of the real `anthropic.Anthropic` surface that `llm_service`
works without hitting the network. Tests monkey-patch
`llm_service._get_client` to return an instance of `FakeAnthropic`.
"""

from __future__ import annotations

import json
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
        # HSK exercises: one valid short_mcq item, plus one broken item that must be dropped.
        self.exercise_response: dict[str, Any] = {
            "items": [
                {
                    "audio": "男：你喜欢喝茶吗？\n女：喜欢，我每天都喝。",
                    "q": "女的每天喝什么？",
                    "fr": "— Tu aimes le thé ? — Oui, j'en bois tous les jours.",
                    "qfr": "Que boit la femme tous les jours ?",
                    "options": ["茶", "水", "牛奶"],
                    "ofr": ["du thé", "de l'eau", "du lait"],
                    "answer": "A",
                },
                {"audio": "男：你好", "q": "?", "options": ["一", "二"], "answer": "C"},
            ]
        }
        self.sentence_check_response: dict[str, Any] = {
            "correct": True,
            "uses_word": True,
            "corrected": "我经常去图书馆。",
            "pinyin": "wǒ jīngcháng qù túshūguǎn.",
            "translation": "Je vais souvent à la bibliothèque.",
            "explanation": "Phrase correcte et naturelle.",
        }
        # Classifier sentences: two valid, then one with an unknown classifier, one with a
        # duplicated wrong option and one with out-of-level characters (all three dropped).
        self.classifier_response: dict[str, Any] = {
            "items": [
                {"zh": "我有一{本}新书。", "wrong": ["家", "杯", "件"], "fr": "J'ai un nouveau livre."},
                {"zh": "他喝了两{杯}水。", "wrong": ["本", "家", "件"], "fr": "Il a bu deux verres d'eau."},
                {"zh": "我有一{艘}船。", "wrong": ["本", "张", "件"], "fr": "J'ai un bateau."},
                {"zh": "我买了一{本}书。", "wrong": ["家", "家", "件"], "fr": "J'ai acheté un livre."},
                {"zh": "我看了一{本}鲲鹏饕餮书。", "wrong": ["家", "杯", "件"], "fr": "?"},
            ]
        }
        self.create_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeMessage:
        self.create_calls.append(kwargs)
        system_text = "".join(block.get("text", "") for block in kwargs.get("system", []))
        if "classificateurs (量词)" in system_text:
            response = self.classifier_response
        elif "concepteur d'épreuves" in system_text:
            response = self.exercise_response
        elif "用词造句" in system_text:
            response = self.sentence_check_response
        elif "phrase d'exemple" in system_text:
            response = self.example_response
        else:
            response = self.subject_response
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
