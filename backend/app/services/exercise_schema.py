"""Shape of HSK exercise items: one parser for the reviewed bank and for Claude's output.

Authoring format (YAML in `data/exercises/src`, JSON from Claude), per type:

- pic_choice / pic_answer: audio, fr, options (3 picture descriptions in French), answer "A"-"C"
- pic_judge: audio, fr, picture (French description), answer true/false
- pic_match / word_match: options (6 pictures or 6 words), items: 5 × {audio, fr, answer "A"-"F"}
- short_mcq / long_mcq / passage_mcq: audio, q, fr, qfr, options (3, Chinese), ofr, answer "A"-"C"
- passage_judge: audio, fr, statement, sfr, answer true/false
- char_pinyin: sentence with the blank as （pinyin）, answer (the character(s)), fr
- reorder: words (space separated), answer (the sentence), alt (other correct orders), fr
- make_sentence: word, reference (a model sentence), fr

`audio` is one line per speaker turn; "男：" / "女：" mark the speaker.
"""

from __future__ import annotations

import re
from typing import Any

ITEM_TYPES = (
    "pic_choice",
    "pic_answer",
    "pic_judge",
    "pic_match",
    "word_match",
    "short_mcq",
    "long_mcq",
    "passage_mcq",
    "passage_judge",
    "char_pinyin",
    "reorder",
    "make_sentence",
)
LETTERS = "ABCDEF"
SPEAKERS = {"男": "m", "女": "f"}
_BLANK = re.compile(r"[（(]\s*([a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüê\s']+)\s*[）)]")
_HAN = re.compile(r"[一-鿿]")


class InvalidItem(ValueError):
    pass


def _text(raw: dict, key: str, required: bool = True) -> str:
    value = raw.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise InvalidItem(f"champ « {key} » manquant")
        return ""
    return str(value).strip()


def parse_audio(script: str) -> list[dict[str, str]]:
    lines = []
    for line in str(script).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        speaker = "n"
        match = re.match(r"^(男|女)\s*[：:]\s*(.+)$", line)
        if match:
            speaker, line = SPEAKERS[match.group(1)], match.group(2).strip()
        lines.append({"s": speaker, "t": line})
    if not lines or not any(_HAN.search(line["t"]) for line in lines):
        raise InvalidItem("audio vide ou sans chinois")
    return lines


def _letter(raw: Any, n: int) -> int:
    letter = str(raw).strip().upper()[:1]
    if letter not in LETTERS[:n]:
        raise InvalidItem(f"réponse « {raw} » hors de A–{LETTERS[n - 1]}")
    return LETTERS.index(letter)


def _bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in {"true", "vrai", "✓", "√", "对", "yes", "1"}:
        return True
    if value in {"false", "faux", "✗", "×", "x", "错", "no", "0"}:
        return False
    raise InvalidItem(f"réponse vrai/faux illisible : {raw}")


def _options(raw: dict, n: int, key: str = "options") -> list[str]:
    options = raw.get(key)
    if not isinstance(options, list) or len(options) != n or not all(str(o).strip() for o in options):
        raise InvalidItem(f"il faut exactement {n} options")
    options = [str(o).strip() for o in options]
    if len(set(options)) != n:
        raise InvalidItem("options en double")
    return options


def normalize(raw: dict[str, Any], item_type: str, level: int) -> dict[str, Any]:
    """Validate an authored / generated item and return the shape the app uses."""
    if item_type not in ITEM_TYPES:
        raise InvalidItem(f"type inconnu : {item_type}")
    item: dict[str, Any] = {"type": item_type, "level": level}

    if item_type in ("pic_choice", "pic_answer"):
        item |= {
            "audio": parse_audio(_text(raw, "audio")),
            "fr": _text(raw, "fr"),
            "options": _options(raw, 3),
            "answer": _letter(raw.get("answer"), 3),
        }
    elif item_type == "pic_judge":
        item |= {
            "audio": parse_audio(_text(raw, "audio")),
            "fr": _text(raw, "fr"),
            "picture": _text(raw, "picture"),
            "answer": _bool(raw.get("answer")),
        }
    elif item_type in ("pic_match", "word_match"):
        options = _options(raw, 6)
        questions = raw.get("items")
        if not isinstance(questions, list) or len(questions) != 5:
            raise InvalidItem("il faut exactement 5 questions par série")
        parsed = [
            {
                "audio": parse_audio(_text(q, "audio")),
                "fr": _text(q, "fr"),
                "answer": _letter(q.get("answer"), 6),
            }
            for q in questions
        ]
        if len({q["answer"] for q in parsed}) != 5:
            raise InvalidItem("chaque option ne sert qu'une fois dans une série")
        if item_type == "word_match":
            for q in parsed:
                heard = "".join(line["t"] for line in q["audio"])
                if options[q["answer"]] not in heard:
                    raise InvalidItem(f"le mot « {options[q['answer']]} » n'est pas dans le dialogue")
                others = [o for i, o in enumerate(options) if i != q["answer"] and o in heard]
                if others:
                    raise InvalidItem(f"le dialogue contient aussi « {others[0]} » : ambigu")
        item |= {"options": options, "items": parsed}
    elif item_type in ("short_mcq", "long_mcq", "passage_mcq"):
        item |= {
            "audio": parse_audio(_text(raw, "audio")),
            "question": _text(raw, "q"),
            "fr": _text(raw, "fr"),
            "question_fr": _text(raw, "qfr"),
            "options": _options(raw, 3),
            "options_fr": _options(raw, 3, "ofr") if raw.get("ofr") else [],
            "answer": _letter(raw.get("answer"), 3),
        }
        turns = len(item["audio"])
        if item_type == "long_mcq" and turns < 4:
            raise InvalidItem("un dialogue long a au moins 4 répliques")
        if item_type == "short_mcq" and turns > 2:
            raise InvalidItem("un dialogue court a au plus 2 répliques")
    elif item_type == "passage_judge":
        item |= {
            "audio": parse_audio(_text(raw, "audio")),
            "fr": _text(raw, "fr"),
            "statement": _text(raw, "statement").lstrip("★ ").strip(),
            "statement_fr": _text(raw, "sfr"),
            "answer": _bool(raw.get("answer")),
        }
    elif item_type == "char_pinyin":
        sentence = _text(raw, "sentence")
        match = _BLANK.search(sentence)
        if not match:
            raise InvalidItem("la phrase doit contenir le trou sous la forme （pinyin）")
        answer = _text(raw, "answer")
        if not _HAN.fullmatch(answer) and not all(_HAN.fullmatch(c) for c in answer):
            raise InvalidItem("la réponse doit être en caractères chinois")
        item |= {
            "before": sentence[: match.start()],
            "pinyin": " ".join(match.group(1).split()),
            "after": sentence[match.end():],
            "answer": answer,
            "fr": _text(raw, "fr"),
        }
    elif item_type == "reorder":
        words = _text(raw, "words").split()
        answer = _text(raw, "answer")
        alts = [str(a).strip() for a in (raw.get("alt") or []) if str(a).strip()]
        strip = lambda s: re.sub(r"[。？！，、?!,.\s]", "", s)  # noqa: E731
        for sentence in [answer, *alts]:
            if sorted(strip(sentence)) != sorted("".join(words)):
                raise InvalidItem(f"« {sentence} » n'utilise pas exactement les mots donnés")
        if len(words) < 3:
            raise InvalidItem("au moins 3 morceaux à remettre dans l'ordre")
        item |= {"words": words, "answers": [answer, *alts], "fr": _text(raw, "fr")}
    elif item_type == "make_sentence":
        word = _text(raw, "word")
        reference = _text(raw, "reference")
        if word not in reference:
            raise InvalidItem("la phrase modèle doit contenir le mot")
        item |= {"word": word, "reference": reference, "fr": _text(raw, "fr")}
    return item


def chinese_texts(item: dict[str, Any]) -> list[str]:
    """Every Chinese string of an item (for the vocabulary check)."""
    texts: list[str] = []
    for line in item.get("audio", []):
        texts.append(line["t"])
    for key in ("question", "statement", "before", "after", "reference", "word"):
        if item.get(key):
            texts.append(item[key])
    if item["type"] in ("short_mcq", "long_mcq", "passage_mcq", "word_match"):
        texts += item["options"]
    for q in item.get("items", []):
        texts += [line["t"] for line in q["audio"]]
    if item["type"] == "reorder":
        texts += item["answers"]
    if item["type"] == "char_pinyin":
        texts = [t for t in texts if t not in (item["before"], item["after"])]
        texts.append(item["before"] + item["answer"] + item["after"])
    return texts
