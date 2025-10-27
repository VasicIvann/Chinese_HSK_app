"""Page principale pour la compréhension écrite (quiz vocabulaire)."""

from __future__ import annotations

import random
import re
import unicodedata
from typing import Dict, List, Literal, Optional, Tuple, cast

import streamlit as st

from repo import get_entries, list_quizzes, set_user_setting
from seed import ensure_seeded
from utils.auth_ui import ensure_user_settings_loaded, init_auth_state, show_auth_notice
from utils.ui import render_top_nav, trigger_rerun

QuestionType = Literal[
    "hanzi_to_translation_input",
    "hanzi_to_pinyin_input",
    "translation_to_hanzi_mcq",
    "hanzi_to_translation_mcq",
]

PinyinVariant = Literal["with_tones", "without_tones"]

QUESTION_TYPE_LABELS: Dict[QuestionType, str] = {
    "hanzi_to_translation_input": "Voir caractères → écrire traduction",
    "hanzi_to_pinyin_input": "Voir caractères → écrire pinyin",
    "translation_to_hanzi_mcq": "Voir mot FR → sélectionner caractère",
    "hanzi_to_translation_mcq": "Voir caractère → sélectionner traduction",
}

DEFAULT_QUESTION_TYPE: QuestionType = "hanzi_to_translation_mcq"
DEFAULT_PINYIN_VARIANT: PinyinVariant = "with_tones"

PINYIN_VARIANT_LABELS: Dict[PinyinVariant, str] = {
    "without_tones": "Sans tons (tons ignorés)",
    "with_tones": "Avec tons (ton à choisir)",
}

PINYIN_SYLLABLE_RE = re.compile(r"(?iu)[a-züv\u00c0-\u024f]+[1-5]?")
NON_WORD_PATTERN = re.compile(r"[^a-z0-9]+")

PINYIN_DIACRITIC_MAP: Dict[str, Tuple[str, int]] = {
    "ā": ("a", 1),
    "á": ("a", 2),
    "ǎ": ("a", 3),
    "à": ("a", 4),
    "Ā": ("a", 1),
    "Á": ("a", 2),
    "Ǎ": ("a", 3),
    "À": ("a", 4),
    "ē": ("e", 1),
    "é": ("e", 2),
    "ě": ("e", 3),
    "è": ("e", 4),
    "Ē": ("e", 1),
    "É": ("e", 2),
    "Ě": ("e", 3),
    "È": ("e", 4),
    "ī": ("i", 1),
    "í": ("i", 2),
    "ǐ": ("i", 3),
    "ì": ("i", 4),
    "Ī": ("i", 1),
    "Í": ("i", 2),
    "Ǐ": ("i", 3),
    "Ì": ("i", 4),
    "ō": ("o", 1),
    "ó": ("o", 2),
    "ǒ": ("o", 3),
    "ò": ("o", 4),
    "Ō": ("o", 1),
    "Ó": ("o", 2),
    "Ǒ": ("o", 3),
    "Ò": ("o", 4),
    "ū": ("u", 1),
    "ú": ("u", 2),
    "ǔ": ("u", 3),
    "ù": ("u", 4),
    "Ū": ("u", 1),
    "Ú": ("u", 2),
    "Ǔ": ("u", 3),
    "Ù": ("u", 4),
    "ǖ": ("v", 1),
    "ǘ": ("v", 2),
    "ǚ": ("v", 3),
    "ǜ": ("v", 4),
    "Ǖ": ("v", 1),
    "Ǘ": ("v", 2),
    "Ǚ": ("v", 3),
    "Ǜ": ("v", 4),
    "ń": ("n", 2),
    "ň": ("n", 3),
    "ǹ": ("n", 4),
    "Ń": ("n", 2),
    "Ň": ("n", 3),
    "Ǹ": ("n", 4),
    "ḿ": ("m", 2),
    "ṁ": ("m", 2),
}


TONE_LABELS: Dict[int, str] = {
    0: "Ton neutre (0)",
    1: "Ton 1",
    2: "Ton 2",
    3: "Ton 3",
    4: "Ton 4",
}
TONE_OPTIONS: List[int] = list(TONE_LABELS.keys())


def split_alt_translations(value: str) -> List[str]:
    """Convert alternate translations into a clean list of synonyms."""
    if not value:
        return []

    candidates = re.split(r"[;\n]", value)
    results: List[str] = []
    for candidate in candidates:
        cleaned = candidate.strip().strip("/").strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("cl:"):
            continue

        # If no semicolons were present, fall back to comma separation.
        if ";" not in value and "," in cleaned:
            parts = [part.strip() for part in cleaned.split(",")]
        else:
            parts = [cleaned]

        for part in parts:
            if not part or part.lower().startswith("cl:"):
                continue
            results.append(part)
    return results


def normalize_text_answer(value: str) -> str:
    """Normalize text answers for forgiving comparisons."""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.replace("’", "'")
    normalized = normalized.replace("-", " ")
    normalized = NON_WORD_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("'", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def gather_translation_answers(entry: Dict[str, str]) -> List[str]:
    """Return the list of accepted translations for a vocabulary entry."""
    answers = [entry.get("translation", "")]
    answers.extend(split_alt_translations(entry.get("alt_translations", "")))
    return [answer for answer in answers if answer]


def normalize_pinyin_value(value: str) -> Tuple[Tuple[str, int], ...]:
    """Return a canonical representation of pinyin supporting tones and digits."""
    if not value:
        return tuple()

    tokens: List[Tuple[str, int]] = []
    for match in PINYIN_SYLLABLE_RE.finditer(value):
        raw_token = match.group()
        token = raw_token.replace("U:", "Ü").replace("u:", "ü").replace("V", "Ü").replace("v", "ü")
        base_chars: List[str] = []
        tone = 0

        for char in token:
            if char in {"'", "’", "˙"}:
                continue
            if char.isdigit():
                digit = int(char)
                if 1 <= digit <= 4:
                    tone = digit
                continue
            if char in PINYIN_DIACRITIC_MAP:
                base, mapped_tone = PINYIN_DIACRITIC_MAP[char]
                base_chars.append(base)
                tone = mapped_tone
                continue
            if char in {"ü", "Ü"}:
                base_chars.append("v")
                continue
            normalized_char = unicodedata.normalize("NFKD", char)
            stripped = "".join(
                c for c in normalized_char if unicodedata.category(c) != "Mn"
            )
            if stripped:
                base_chars.append(stripped.lower())

        base = "".join(base_chars)
        if not base:
            continue
        tokens.append((base, tone))

    return tuple(tokens)


def _ensure_score_banner_style() -> None:
    """Inject CSS once for the live score banner."""
    if st.session_state.get("_score_banner_css_injected"):
        return

    st.markdown(
        """
        <style>
        .live-score-banner {
            background: linear-gradient(135deg, #0f172a, #172554);
            border-radius: 14px;
            padding: 1.25rem;
            color: #f8fafc;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.35);
        }
        .live-score-banner__row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        .live-score-banner__value {
            font-size: 1.1rem;
        }
        .live-score-banner__track {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.28);
            overflow: hidden;
            margin-bottom: 0.35rem;
        }
        .live-score-banner__fill {
            height: 100%;
            border-radius: 999px;
            background: #38bdf8;
        }
        .live-score-banner__hint {
            font-size: 0.85rem;
            color: rgba(248, 250, 252, 0.85);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_score_banner_css_injected"] = True


def render_live_score_banner() -> None:
    """Display a live percentage banner for correct answers."""
    _ensure_score_banner_style()
    history = st.session_state.get("history") or []
    answered = len(history)
    score = st.session_state.get("score", 0)
    percentage = round((score / answered) * 100) if answered else 0
    detail = (
        f"{score} bonne(s) réponse(s) sur {answered} tentative(s) validées."
        if answered
        else "Répondez à une question pour voir votre score en temps réel."
    )
    st.markdown(
        f"""
        <div class="live-score-banner">
            <div class="live-score-banner__row">
                <span>Score en temps réel</span>
                <span class="live-score-banner__value">{percentage}% de bonnes réponses</span>
            </div>
            <div class="live-score-banner__track">
                <div class="live-score-banner__fill" style="width: {percentage}%"></div>
            </div>
            <div class="live-score-banner__hint">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def strip_pinyin_tones(tokens: Tuple[Tuple[str, int], ...]) -> Tuple[str, ...]:
    """Return the syllable sequence without tone information."""
    return tuple(base for base, _ in tokens)


def build_structured_pinyin_submission(
    syllables: List[str], tones: List[int]
) -> Tuple[str, bool]:
    """Combine syllable inputs and tone selections into a single answer string."""
    missing = any(not syllable.strip() for syllable in syllables)
    parts = []
    for syllable, tone in zip(syllables, tones):
        base = syllable.strip()
        if not base:
            continue
        suffix = "" if tone == 0 else str(tone)
        parts.append(f"{base}{suffix}")
    return " ".join(parts).strip(), missing


def get_question_pinyin_tokens(question: Dict[str, object]) -> Tuple[Tuple[str, int], ...]:
    """Fetch normalized pinyin tokens from a question definition."""
    raw_tokens = question.get("normalized_pinyin")
    if isinstance(raw_tokens, tuple):
        return cast(Tuple[Tuple[str, int], ...], raw_tokens)
    raw_value = str(question.get("pinyin", ""))
    return normalize_pinyin_value(raw_value)


def format_tone_choice(option: int) -> str:
    """Return the human-readable label for a tone selector."""
    return TONE_LABELS.get(option, f"Ton {option}")


def clear_pinyin_variant_inputs(question_index: int, syllable_count: int) -> None:
    """Clear stored syllable and tone inputs for a question index."""
    total = max(1, syllable_count)
    for idx in range(total):
        st.session_state.pop(f"pinyin_syllable_{question_index}_{idx}", None)
        st.session_state.pop(f"pinyin_tone_{question_index}_{idx}", None)


def build_question_pool(
    vocab: List[Dict[str, str]],
    num_questions: int,
    question_type: QuestionType,
    num_choices: int = 4,
    seed: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Build a randomized quiz question list for the selected mode."""
    rng = random.Random(seed)
    total_questions = min(num_questions, len(vocab))
    selected = rng.sample(vocab, k=total_questions)

    questions: List[Dict[str, object]] = []
    for entry in selected:
        question: Dict[str, object] = {
            "hanzi": entry["hanzi"],
            "pinyin": entry["pinyin"],
            "translation": entry["translation"],
            "alt_translations": entry.get("alt_translations", ""),
            "type": question_type,
        }

        if question_type == "hanzi_to_translation_input":
            accepted = gather_translation_answers(entry)
            question["accepted_translations"] = {
                normalize_text_answer(answer) for answer in accepted
            }
            question["accepted_answers_raw"] = accepted
            question["correct"] = entry["translation"]

        elif question_type == "hanzi_to_pinyin_input":
            question["normalized_pinyin"] = normalize_pinyin_value(entry["pinyin"])
            question["correct"] = entry["pinyin"]

        elif question_type == "translation_to_hanzi_mcq":
            incorrect_pool = [item["hanzi"] for item in vocab if item["hanzi"] != entry["hanzi"]]
            choice_count = min(num_choices - 1, len(incorrect_pool))
            incorrect_choices = (
                rng.sample(incorrect_pool, k=choice_count) if choice_count > 0 else []
            )
            choices = incorrect_choices + [entry["hanzi"]]
            rng.shuffle(choices)
            question["choices"] = choices
            question["correct"] = entry["hanzi"]

        elif question_type == "hanzi_to_translation_mcq":
            incorrect_pool = [
                item["translation"]
                for item in vocab
                if item["translation"] != entry["translation"]
            ]
            choice_count = min(num_choices - 1, len(incorrect_pool))
            incorrect_choices = (
                rng.sample(incorrect_pool, k=choice_count) if choice_count > 0 else []
            )
            choices = incorrect_choices + [entry["translation"]]
            rng.shuffle(choices)
            question["choices"] = choices
            question["correct"] = entry["translation"]

        else:
            raise ValueError(f"Unsupported question type: {question_type}")

        questions.append(question)

    return questions


def reset_quiz(
    quiz_key: str, num_questions: int, question_type: QuestionType, seed: Optional[int] = None
) -> None:
    """Initialize session state for a new quiz."""
    for key in list(st.session_state.keys()):
        if key.startswith("hint_shown_") or key.startswith("pinyin_syllable_") or key.startswith(
            "pinyin_tone_"
        ):
            st.session_state.pop(key)

    vocab = get_entries(quiz_key)
    st.session_state["vocab"] = vocab
    st.session_state["selected_quiz"] = quiz_key
    st.session_state["question_type"] = question_type

    if not vocab:
        st.session_state["num_questions"] = 0
        st.session_state["questions"] = []
        st.session_state["current_idx"] = 0
        st.session_state["score"] = 0
        st.session_state["answered"] = False
        st.session_state["last_choice"] = None
        st.session_state["feedback"] = ""
        st.session_state["history"] = []
        return

    total_questions = min(num_questions, len(vocab))
    st.session_state["num_questions"] = total_questions
    st.session_state["questions"] = build_question_pool(
        vocab, total_questions, question_type=question_type, seed=seed
    )
    st.session_state["current_idx"] = 0
    st.session_state["score"] = 0
    st.session_state["answered"] = False
    st.session_state["last_choice"] = None
    st.session_state["feedback"] = ""
    st.session_state["history"] = []


def evaluate_answer(submission: Optional[str]) -> None:
    """Evaluate the submitted answer and update session state."""
    idx = st.session_state["current_idx"]
    question = st.session_state["questions"][idx]
    question_type: QuestionType = question.get("type", DEFAULT_QUESTION_TYPE)  # type: ignore[arg-type]
    user_answer = (submission or "").strip()
    is_correct = False
    feedback = ""
    correct_display = question.get("correct", "")

    if question_type == "hanzi_to_translation_input":
        normalized_input = normalize_text_answer(user_answer) if user_answer else ""
        accepted_raw = question.get("accepted_translations")
        accepted = accepted_raw if isinstance(accepted_raw, set) else set()
        is_correct = bool(normalized_input) and normalized_input in accepted
        if is_correct:
            feedback = "Bonne réponse !"
        else:
            synonyms = question.get("accepted_answers_raw", [])
            if synonyms:
                feedback = "Mauvaise réponse. Traductions acceptées : " + ", ".join(synonyms)
            else:
                feedback = f"Mauvaise réponse. Traduction attendue : **{correct_display}**."

    elif question_type == "hanzi_to_pinyin_input":
        variant: PinyinVariant = st.session_state.get("pinyin_variant", DEFAULT_PINYIN_VARIANT)
        normalized_input = normalize_pinyin_value(user_answer)
        expected = get_question_pinyin_tokens(question)
        if variant == "without_tones":
            is_correct = bool(normalized_input) and strip_pinyin_tones(normalized_input) == strip_pinyin_tones(
                expected
            )
        else:
            is_correct = bool(normalized_input) and normalized_input == expected
        if is_correct:
            feedback = "Bonne réponse !"
        else:
            feedback = f"Pinyin attendu : **{correct_display}**."

    elif question_type == "translation_to_hanzi_mcq":
        is_correct = user_answer == correct_display
        feedback = "Bonne réponse !" if is_correct else f"Mauvaise réponse. Le caractère correct est **{correct_display}**."

    else:
        is_correct = user_answer == correct_display
        feedback = "Bonne réponse !" if is_correct else f"Mauvaise réponse. La bonne traduction est **{correct_display}**."

    st.session_state["answered"] = True
    st.session_state["last_choice"] = user_answer
    if is_correct:
        st.session_state["score"] += 1
    st.session_state["feedback"] = feedback

    st.session_state["history"].append(
        {
            "hanzi": question["hanzi"],
            "pinyin": question["pinyin"],
            "correct": question.get("correct"),
            "translation": question.get("translation"),
            "question_type": question_type,
            "user_choice": user_answer,
            "is_correct": is_correct,
        }
    )


def render_summary() -> None:
    """Display final quiz summary."""
    score = st.session_state.get("score", 0)
    total = st.session_state.get("num_questions", len(st.session_state.get("questions", [])))
    st.success(f"Quiz terminé ! Vous avez {score} bonne(s) réponse(s) sur {total}.")

    quiz_meta = st.session_state.get("quiz_meta")
    if quiz_meta:
        st.caption(f"Quiz sélectionné : {quiz_meta['title']}")

    details = []
    for entry in st.session_state.get("history", []):
        status = "✅" if entry["is_correct"] else "❌"
        question_type = entry.get("question_type", DEFAULT_QUESTION_TYPE)
        question_label = (
            entry.get("translation") if question_type == "translation_to_hanzi_mcq" else entry["hanzi"]
        )
        details.append(
            {
                "Type": QUESTION_TYPE_LABELS.get(question_type, question_type),
                "Question": question_label or "",
                "Pinyin": entry["pinyin"],
                "Votre réponse": entry["user_choice"],
                "Bonne réponse": entry["correct"],
                "Résultat": status,
            }
        )
    if details:
        st.subheader("Vos réponses")
        st.table(details)


def render_quiz() -> None:
    """Render the quiz interface."""
    idx = st.session_state["current_idx"]
    questions = st.session_state["questions"]
    question = questions[idx]
    total = len(questions)

    st.write(f"Question {idx + 1} sur {total}")
    st.progress((idx + 1) / total)

    question_type: QuestionType = question.get("type", DEFAULT_QUESTION_TYPE)  # type: ignore[arg-type]
    hint_key = f"hint_shown_{idx}"
    hint_entries: List[Tuple[str, str]] = []

    if question_type == "translation_to_hanzi_mcq":
        st.markdown(f"### {question['translation']}")
        pinyin_hint = question.get("pinyin")
        if pinyin_hint:
            hint_entries.append(("Indice pinyin", str(pinyin_hint)))
    else:
        st.markdown(f"### {question['hanzi']}")
        if question_type == "hanzi_to_pinyin_input":
            translation_hint = question.get("translation")
            if translation_hint:
                hint_entries.append(("Traduction", str(translation_hint)))
        else:
            pinyin_hint = question.get("pinyin")
            if pinyin_hint:
                hint_entries.append(("Pinyin", str(pinyin_hint)))

    if hint_entries:
        if st.session_state.get(hint_key):
            for label, value in hint_entries:
                st.caption(f"{label} : {value}")
        else:
            if st.button("Révéler les indices", key=f"reveal_hint_{idx}"):
                st.session_state[hint_key] = True
                trigger_rerun()
            else:
                st.caption('Indices masqués. Cliquez sur "Révéler les indices" si besoin.')

    if not st.session_state["answered"]:
        form_key = f"quiz_form_{idx}"
        missing_syllables = False
        choice: Optional[str] = None
        with st.form(key=form_key):
            if question_type in {"hanzi_to_translation_mcq", "translation_to_hanzi_mcq"}:
                label = (
                    "Choisissez la traduction correcte :"
                    if question_type == "hanzi_to_translation_mcq"
                    else "Choisissez le caractère correct :"
                )
                choice = st.selectbox(
                    label,
                    question.get("choices", []),
                    index=None,
                    placeholder="Sélectionnez une réponse",
                    key=f"choice_select_{idx}",
                )
            elif question_type == "hanzi_to_translation_input":
                label = "Entrez la traduction en français"
                placeholder = "Ex. : aimer / apprécier"
                input_key = f"text_answer_{idx}"
                choice = st.text_input(
                    label,
                    value=st.session_state.get(input_key, ""),
                    key=input_key,
                    placeholder=placeholder,
                )
            else:
                pinyin_variant: PinyinVariant = st.session_state.get(
                    "pinyin_variant", DEFAULT_PINYIN_VARIANT
                )
                if pinyin_variant == "without_tones":
                    label = "Entrez le pinyin (tons ignorés)"
                    placeholder = "Ex. : ni hao"
                    input_key = f"text_answer_{idx}"
                    choice = st.text_input(
                        label,
                        value=st.session_state.get(input_key, ""),
                        key=input_key,
                        placeholder=placeholder,
                    )
                else:
                    tokens = get_question_pinyin_tokens(question)
                    syllable_count = max(1, len(tokens))
                    st.caption("Saisissez chaque syllabe et choisissez son ton.")
                    syllable_inputs: List[str] = []
                    tone_inputs: List[int] = []
                    for syllable_idx in range(syllable_count):
                        cols = st.columns([3, 1])
                        placeholder_value = (
                            tokens[syllable_idx][0] if syllable_idx < len(tokens) else ""
                        )
                        syllable_inputs.append(
                            cols[0].text_input(
                                f"Syllabe {syllable_idx + 1}",
                                key=f"pinyin_syllable_{idx}_{syllable_idx}",
                                placeholder=placeholder_value or f"Syllabe {syllable_idx + 1}",
                            )
                        )
                        tone_inputs.append(
                            cols[1].selectbox(
                                f"Ton {syllable_idx + 1}",
                                options=TONE_OPTIONS,
                                format_func=format_tone_choice,
                                key=f"pinyin_tone_{idx}_{syllable_idx}",
                            )
                        )
                    choice, missing_syllables = build_structured_pinyin_submission(
                        syllable_inputs, tone_inputs
                    )
            submitted = st.form_submit_button("Valider la réponse")

        if submitted:
            if (
                question_type == "hanzi_to_pinyin_input"
                and st.session_state.get("pinyin_variant", DEFAULT_PINYIN_VARIANT) == "with_tones"
                and missing_syllables
            ):
                st.warning("Renseignez toutes les syllabes et leurs tons avant de valider.")
            elif choice is None or (isinstance(choice, str) and not choice.strip()):
                st.warning("Saisissez votre réponse avant de valider.")
            else:
                evaluate_answer(choice if choice is not None else "")
                trigger_rerun()

    else:
        st.info(st.session_state["feedback"])
        correct_answer = question.get("correct", "")
        if question_type == "hanzi_to_pinyin_input":
            st.write(f"Pinyin correct : **{correct_answer}**")
        elif question_type == "translation_to_hanzi_mcq":
            st.write(f"Caractère correct : **{correct_answer}**")
        else:
            st.write(f"Traduction correcte : **{correct_answer}**")

        if st.button("Question suivante", key=f"next_button_{idx}"):
            st.session_state["current_idx"] += 1
            st.session_state["answered"] = False
            st.session_state["last_choice"] = None
            st.session_state["feedback"] = ""
            st.session_state.pop(f"text_answer_{idx}", None)
            st.session_state.pop(f"choice_select_{idx}", None)
            st.session_state.pop(f"hint_shown_{idx}", None)
            token_count = len(get_question_pinyin_tokens(question))
            clear_pinyin_variant_inputs(idx, token_count)
            trigger_rerun()



def main() -> None:
    st.set_page_config(page_title="Comprehension ecrite", page_icon="??", layout="wide")
    ensure_seeded()
    init_auth_state()
    ensure_user_settings_loaded()
    st.session_state.setdefault("pinyin_variant", DEFAULT_PINYIN_VARIANT)

    render_top_nav("comprehension")
    show_auth_notice()

    st.markdown(
        """
        <div class="page-intro">
            <h1>Comprehension ecrite</h1>
            <p>Testez votre vocabulaire HSK et suivez vos progres question apres question.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_live_score_banner()

    quizzes = list_quizzes()
    if not quizzes:
        st.error("Aucun quiz disponible. Verifiez l'initialisation de la base de donnees.")
        return

    quiz_lookup = {quiz["key"]: quiz for quiz in quizzes}
    quiz_keys = list(quiz_lookup.keys())

    default_quiz_key = st.session_state.get("selected_quiz", quiz_keys[0])
    if default_quiz_key not in quiz_lookup:
        default_quiz_key = quiz_keys[0]

    user = st.session_state.get("user")
    st.markdown("### Configurez votre session")
    if user:
        st.caption(f"Connecte en tant que {user['email']}. Vos preferences seront memorisees.")
    else:
        st.info("Astuce: connectez-vous depuis la rubrique Compte pour conserver vos reglages favoris.")

    config_cols = st.columns([2, 1])
    with config_cols[0]:
        selected_quiz_key = st.selectbox(
            "Choisir un quiz",
            options=quiz_keys,
            index=quiz_keys.index(default_quiz_key),
            format_func=lambda key: quiz_lookup[key]["title"],
        )
        selected_meta = quiz_lookup[selected_quiz_key]
        st.session_state["quiz_meta"] = selected_meta
        if selected_meta.get("description"):
            st.caption(selected_meta["description"])

        question_type_options = list(QUESTION_TYPE_LABELS.keys())
        previous_question_type = st.session_state.get("question_type", DEFAULT_QUESTION_TYPE)
        if previous_question_type not in question_type_options:
            previous_question_type = DEFAULT_QUESTION_TYPE

        question_type = st.radio(
            "Type de questions",
            options=question_type_options,
            index=question_type_options.index(previous_question_type),
            format_func=lambda key: QUESTION_TYPE_LABELS[key],
        )
        current_variant: PinyinVariant = st.session_state.get("pinyin_variant", DEFAULT_PINYIN_VARIANT)
        if question_type == "hanzi_to_pinyin_input":
            variant_options = list(PINYIN_VARIANT_LABELS.keys())
            if current_variant not in variant_options:
                current_variant = DEFAULT_PINYIN_VARIANT
            selected_variant = st.radio(
                "Variante pinyin",
                options=variant_options,
                index=variant_options.index(current_variant),
                format_func=lambda key: PINYIN_VARIANT_LABELS[key],
                horizontal=True,
            )
            st.session_state["pinyin_variant"] = selected_variant
        else:
            st.session_state.setdefault("pinyin_variant", DEFAULT_PINYIN_VARIANT)

    vocab = get_entries(selected_quiz_key)
    if not vocab:
        st.warning("Aucune donnee disponible pour ce quiz pour le moment.")
        return

    max_questions = len(vocab)
    default_num = st.session_state.get("num_questions", min(10, max_questions))
    if user:
        stored_default = st.session_state["user_settings"].get("default_num_questions")
        if stored_default:
            try:
                default_num = int(stored_default)
            except ValueError:
                default_num = st.session_state.get("num_questions", min(10, max_questions))

    default_num = max(1, min(default_num, max_questions))

    with config_cols[1]:
        num_questions = st.slider(
            "Nombre de questions",
            min_value=1,
            max_value=max_questions,
            value=default_num,
        )

    st.session_state["num_questions"] = num_questions
    if user:
        stored_value = st.session_state["user_settings"].get("default_num_questions")
        if stored_value != str(num_questions):
            set_user_setting(user["id"], "default_num_questions", str(num_questions))
            st.session_state["user_settings"]["default_num_questions"] = str(num_questions)

    quiz_changed = st.session_state.get("selected_quiz") != selected_quiz_key
    type_changed = question_type != previous_question_type
    if "questions" not in st.session_state or quiz_changed or type_changed:
        reset_quiz(selected_quiz_key, num_questions, question_type)
        if quiz_changed or type_changed:
            trigger_rerun()
            return

    total_questions = len(st.session_state.get("questions", []))
    current_score = st.session_state.get("score", 0)
    current_idx = st.session_state.get("current_idx", 0)

    stats_cols = st.columns([1, 1, 1])
    stats_cols[0].metric("Score", f"{current_score} / {total_questions}")
    stats_cols[1].metric(
        "Question",
        f"{min(current_idx + 1, total_questions) if total_questions else 0} / {total_questions}",
    )
    with stats_cols[2]:
        if st.button("Nouvelle serie", use_container_width=True):
            seed_value = random.randint(0, 10_000)
            reset_quiz(selected_quiz_key, num_questions, question_type, seed=seed_value)
            trigger_rerun()
            return

    st.divider()
    st.subheader(selected_meta["title"])
    if selected_meta.get("description"):
        st.caption(selected_meta["description"])

    if not st.session_state.get("questions"):
        st.info("Veuillez ajouter des entrees de vocabulaire pour ce quiz.")
        return

    if st.session_state["current_idx"] >= len(st.session_state["questions"]):
        render_summary()
    else:
        render_quiz()


if __name__ == "__main__":
    main()
