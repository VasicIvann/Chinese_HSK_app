"""Page principale pour la compréhension écrite (quiz vocabulaire)."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

import streamlit as st

from repo import get_entries, list_quizzes
from seed import ensure_seeded
from utils.ui import trigger_rerun


def build_question_pool(
    vocab: List[Dict[str, str]],
    num_questions: int,
    num_choices: int = 4,
    seed: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Build a randomized quiz question list."""
    rng = random.Random(seed)
    translations = [entry["translation"] for entry in vocab]
    total_questions = min(num_questions, len(vocab))
    selected = rng.sample(vocab, k=total_questions)

    questions = []
    for entry in selected:
        incorrect_pool = [t for t in translations if t != entry["translation"]]
        choice_count = min(num_choices - 1, len(incorrect_pool))
        incorrect_choices = rng.sample(incorrect_pool, k=choice_count) if choice_count > 0 else []
        choices = incorrect_choices + [entry["translation"]]
        rng.shuffle(choices)
        questions.append(
            {
                "hanzi": entry["hanzi"],
                "pinyin": entry["pinyin"],
                "correct": entry["translation"],
                "choices": choices,
            }
        )
    return questions


def reset_quiz(quiz_key: str, num_questions: int, seed: Optional[int] = None) -> None:
    """Initialize session state for a new quiz."""
    vocab = get_entries(quiz_key)
    st.session_state["vocab"] = vocab
    st.session_state["selected_quiz"] = quiz_key

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
    st.session_state["questions"] = build_question_pool(vocab, total_questions, seed=seed)
    st.session_state["current_idx"] = 0
    st.session_state["score"] = 0
    st.session_state["answered"] = False
    st.session_state["last_choice"] = None
    st.session_state["feedback"] = ""
    st.session_state["history"] = []


def evaluate_answer(choice: str) -> None:
    """Evaluate the selected answer and update session state."""
    idx = st.session_state["current_idx"]
    question = st.session_state["questions"][idx]
    is_correct = choice == question["correct"]

    st.session_state["answered"] = True
    st.session_state["last_choice"] = choice
    if is_correct:
        st.session_state["score"] += 1
        st.session_state["feedback"] = "✅ Bonne réponse !"
    else:
        st.session_state["feedback"] = (
            f"❌ Mauvaise réponse. La bonne traduction est **{question['correct']}**."
        )

    st.session_state["history"].append(
        {
            "hanzi": question["hanzi"],
            "pinyin": question["pinyin"],
            "correct": question["correct"],
            "user_choice": choice,
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
        details.append(
            {
                "Mot": entry["hanzi"],
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

    st.markdown(f"### {question['hanzi']}")
    st.caption(f"Pinyin : {question['pinyin']}")

    if not st.session_state["answered"]:
        with st.form(key=f"quiz_form_{idx}"):
            choice = st.selectbox(
                "Choisissez la traduction correcte :",
                question["choices"],
                index=None,
                placeholder="Sélectionnez une réponse",
                key=f"choice_select_{idx}",
            )
            submitted = st.form_submit_button("Valider la réponse")

        if submitted:
            if choice is None:
                st.warning("Sélectionnez une réponse avant de valider.")
            else:
                evaluate_answer(choice)
                trigger_rerun()
    else:
        st.info(st.session_state["feedback"])
        correct_answer = question["correct"]
        st.write(f"Traduction correcte : **{correct_answer}**")

        if st.button("Question suivante", key=f"next_button_{idx}"):
            st.session_state["current_idx"] += 1
            st.session_state["answered"] = False
            st.session_state["last_choice"] = None
            st.session_state["feedback"] = ""
            trigger_rerun()


def main() -> None:
    st.set_page_config(page_title="Compréhension écrite", page_icon="🧠", layout="centered")
    ensure_seeded()

    st.title("Compréhension écrite — Quiz de vocabulaire")
    st.write(
        "Entraînez-vous sur les listes officielles HSK en choisissant votre niveau, le nombre de questions "
        "et le mode d'entraînement. D'autres exercices de compréhension seront ajoutés prochainement."
    )

    quizzes = list_quizzes()
    if not quizzes:
        st.error("Aucun quiz disponible. Vérifiez l'initialisation de la base de données.")
        return

    quiz_lookup = {quiz["key"]: quiz for quiz in quizzes}
    quiz_keys = list(quiz_lookup.keys())

    default_quiz_key = st.session_state.get("selected_quiz", quiz_keys[0])
    if default_quiz_key not in quiz_lookup:
        default_quiz_key = quiz_keys[0]

    st.sidebar.header("Paramètres")
    st.sidebar.write("Configurez votre session d'entraînement.")
    selected_quiz_key = st.sidebar.selectbox(
        "Choisir un quiz",
        options=quiz_keys,
        index=quiz_keys.index(default_quiz_key),
        format_func=lambda key: quiz_lookup[key]["title"],
    )
    selected_meta = quiz_lookup[selected_quiz_key]
    st.session_state["quiz_meta"] = selected_meta

    if selected_meta.get("description"):
        st.sidebar.caption(selected_meta["description"])

    vocab = get_entries(selected_quiz_key)
    if not vocab:
        st.warning("Aucune donnée disponible pour ce quiz pour le moment.")
        return

    max_questions = len(vocab)
    default_num = st.session_state.get("num_questions", min(10, max_questions))
    default_num = max(1, min(default_num, max_questions))
    num_questions = st.sidebar.slider(
        "Nombre de questions",
        min_value=1,
        max_value=max_questions,
        value=default_num,
    )
    st.session_state["num_questions"] = num_questions

    quiz_changed = st.session_state.get("selected_quiz") != selected_quiz_key
    if "questions" not in st.session_state or quiz_changed:
        reset_quiz(selected_quiz_key, num_questions)
        if quiz_changed:
            trigger_rerun()
            return

    if st.sidebar.button("Lancer un nouveau quiz"):
        seed_value = random.randint(0, 10_000)
        reset_quiz(selected_quiz_key, num_questions, seed=seed_value)
        trigger_rerun()
        return

    total_questions = len(st.session_state.get("questions", []))
    st.sidebar.metric("Score", f"{st.session_state.get('score', 0)} / {total_questions}")

    st.subheader(selected_meta["title"])
    if selected_meta.get("description"):
        st.caption(selected_meta["description"])

    if not st.session_state.get("questions"):
        st.info("Veuillez ajouter des entrées de vocabulaire pour ce quiz.")
        return

    if st.session_state["current_idx"] >= len(st.session_state["questions"]):
        render_summary()
    else:
        render_quiz()


if __name__ == "__main__":
    main()
