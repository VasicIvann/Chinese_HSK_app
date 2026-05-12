"""Page Expression écrite : production guidée + correction par Claude."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

import llm
from repo import (
    find_entry_ids_by_hanzi,
    get_or_create_daily_usage,
    increment_daily_usage,
    list_expression_attempts,
    record_expression_attempt,
)
from srs import queue_entries_for_relearn
from utils.auth_ui import init_auth_state, show_auth_notice
from utils.ui import render_top_nav, trigger_rerun


SUBJECTS_FILE = Path(__file__).resolve().parent.parent / "data" / "expression_subjects.json"

DEFAULT_LEVEL = 2
DAILY_QUOTA_DEFAULT = 20
USAGE_KIND = "expression_correction"

LEVEL_INFO = {
    1: "1-2 phrases courtes (10-30 caractères)",
    2: "2-4 phrases (30-70 caractères)",
    3: "Petit paragraphe de 4-7 phrases (70-150 caractères)",
}


def _load_subject_pool() -> Dict[int, List[Dict[str, object]]]:
    try:
        raw = json.loads(SUBJECTS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return {int(level): subjects for level, subjects in raw.items()}


def _ensure_state() -> None:
    init_auth_state()
    defaults = {
        "expression_level": DEFAULT_LEVEL,
        "expression_subject": "",
        "expression_subject_keywords": [],
        "expression_user_text": "",
        "expression_correction": None,
        "expression_last_attempt_id": None,
        "expression_relearned": 0,
        "expression_loaded_pool": _load_subject_pool(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _quota_left(user_id: int) -> int:
    usage = get_or_create_daily_usage(user_id, USAGE_KIND)
    return max(0, DAILY_QUOTA_DEFAULT - int(usage.get("count", 0) or 0))


def _render_intro() -> None:
    st.markdown(
        """
        <div class="page-intro">
            <h1>Expression écrite</h1>
            <p>Rédigez en chinois sur un sujet imposé, recevez une correction structurée par IA et alimentez vos révisions SRS.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_configuration(pool: Dict[int, List[Dict[str, object]]]) -> None:
    st.markdown("### Configurez votre session")
    level_options = [1, 2, 3]
    cols = st.columns([1, 2])
    with cols[0]:
        level = st.radio(
            "Niveau HSK",
            options=level_options,
            index=level_options.index(st.session_state["expression_level"]),
            format_func=lambda l: f"HSK {l}",
            horizontal=True,
            key="expression_level_radio",
        )
        st.session_state["expression_level"] = level
        st.caption(f"Longueur attendue : {LEVEL_INFO.get(level, '')}")

    with cols[1]:
        subjects_for_level = pool.get(level, [])
        labels = [s["subject"] for s in subjects_for_level]
        labels_with_default = ["— Sélectionnez un sujet —"] + labels + ["Écrire mon propre sujet"]
        choice = st.selectbox(
            "Sujet imposé",
            options=labels_with_default,
            index=0,
            key=f"expression_subject_choice_{level}",
        )
        if choice == "Écrire mon propre sujet":
            free_subject = st.text_input(
                "Votre sujet personnalisé",
                value=st.session_state.get("expression_subject", ""),
                placeholder="Ex. : Présentez votre meilleur souvenir d'enfance.",
                key=f"expression_free_subject_{level}",
            )
            if free_subject.strip():
                st.session_state["expression_subject"] = free_subject.strip()
                st.session_state["expression_subject_keywords"] = []
        elif choice and choice != "— Sélectionnez un sujet —":
            selected = next(
                (s for s in subjects_for_level if s["subject"] == choice), None
            )
            if selected:
                st.session_state["expression_subject"] = str(selected["subject"])
                st.session_state["expression_subject_keywords"] = list(selected.get("keywords", []))


def _render_generate_button(level: int) -> None:
    if not llm.is_configured():
        return
    if st.button("✨ Générer un nouveau sujet (Claude)", key="generate_subject_btn"):
        try:
            with st.spinner("Génération du sujet en cours…"):
                payload, usage = llm.generate_subject(level=level)
        except llm.LLMNotConfiguredError as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # pragma: no cover - network error path
            st.error(f"Erreur lors de la génération : {exc}")
            return

        subject_text = str(payload.get("subject", "")).strip()
        keywords = [str(k) for k in payload.get("keywords", []) if str(k).strip()]
        if not subject_text:
            st.warning("Le modèle n'a pas renvoyé de sujet exploitable.")
            return

        st.session_state["expression_subject"] = subject_text
        st.session_state["expression_subject_keywords"] = keywords

        user = st.session_state.get("user")
        if user:
            increment_daily_usage(
                user["id"],
                "subject_generation",
                tokens_input_delta=int(usage.get("input_tokens", 0) or 0),
                tokens_output_delta=int(usage.get("output_tokens", 0) or 0),
            )
        st.success("Sujet généré.")
        trigger_rerun()


def _render_subject_card() -> None:
    subject = st.session_state.get("expression_subject", "")
    if not subject:
        st.info("Choisissez ou générez un sujet pour commencer.")
        return

    keywords = st.session_state.get("expression_subject_keywords", []) or []
    st.markdown("### Sujet")
    st.markdown(
        f"""
        <div class="feature-card" style="margin-bottom: 0.75rem;">
            <p style="font-size: 1.1rem; margin: 0;"><strong>{subject}</strong></p>
            {('<p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: rgba(248,250,252,0.78);">Mots-clés HSK suggérés : ' + ", ".join(keywords) + '</p>') if keywords else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_writer(level: int, user_id: int) -> None:
    st.markdown("### Votre production")
    max_chars = llm.LEVEL_MAX_CHARS.get(level, 700)
    text = st.text_area(
        "Écrivez en chinois (caractères han)",
        value=st.session_state.get("expression_user_text", ""),
        height=200,
        max_chars=max_chars,
        key="expression_user_text_input",
        placeholder="例如 : 我今天很高兴…",
    )
    st.session_state["expression_user_text"] = text

    char_count = len(text)
    quota_left = _quota_left(user_id)
    cols = st.columns([1, 1, 1])
    cols[0].metric("Caractères", f"{char_count} / {max_chars}")
    cols[1].metric("Corrections restantes (jour)", f"{quota_left} / {DAILY_QUOTA_DEFAULT}")
    cols[2].metric("Modèle", llm.get_model_id().split("-")[1].capitalize() if "-" in llm.get_model_id() else llm.get_model_id())

    submit_disabled = quota_left <= 0 or not text.strip() or not st.session_state.get("expression_subject")
    if quota_left <= 0:
        st.warning("Quota quotidien atteint. Revenez demain pour de nouvelles corrections.")
    submit = st.button(
        "Demander la correction",
        type="primary",
        disabled=submit_disabled,
        key="submit_correction_btn",
    )

    if submit:
        if not llm.contains_chinese(text):
            st.error("Votre texte ne contient pas de caractères chinois. Écrivez en mandarin pour obtenir une correction.")
            return
        _process_submission(user_id=user_id, level=level, subject=st.session_state["expression_subject"], text=text)


def _process_submission(user_id: int, level: int, subject: str, text: str) -> None:
    try:
        with st.spinner("Claude analyse votre production…"):
            correction, usage = llm.correct_expression(text, level=level, subject=subject)
    except llm.LLMNotConfiguredError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # pragma: no cover - network error path
        st.error(f"Erreur lors de la correction : {exc}")
        return

    score = correction.get("score")
    try:
        score_int = int(score) if score is not None else None
    except (TypeError, ValueError):
        score_int = None

    attempt_id = record_expression_attempt(
        user_id=user_id,
        hsk_level=level,
        subject=subject,
        user_text=text,
        correction=correction,
        score=score_int,
        tokens_input=int(usage.get("input_tokens", 0) or 0),
        tokens_output=int(usage.get("output_tokens", 0) or 0),
        model_id=llm.get_model_id(),
    )

    increment_daily_usage(
        user_id,
        USAGE_KIND,
        count_delta=1,
        tokens_input_delta=int(usage.get("input_tokens", 0) or 0),
        tokens_output_delta=int(usage.get("output_tokens", 0) or 0),
    )

    mistakes_raw = correction.get("vocabulary_mistakes") or []
    mistakes = [str(m).strip() for m in mistakes_raw if str(m).strip()]
    mapping = find_entry_ids_by_hanzi(mistakes)
    entry_ids = list({eid for eid in mapping.values() if eid})
    relearned = queue_entries_for_relearn(user_id, entry_ids) if entry_ids else 0

    st.session_state["expression_correction"] = correction
    st.session_state["expression_last_attempt_id"] = attempt_id
    st.session_state["expression_relearned"] = relearned


def _render_correction() -> None:
    correction = st.session_state.get("expression_correction")
    if not correction:
        return

    st.markdown("### Correction Claude")
    score = correction.get("score")
    cols = st.columns([1, 2])
    if isinstance(score, int):
        cols[0].metric("Score", f"{score} / 100")
    relearned = int(st.session_state.get("expression_relearned", 0) or 0)
    if relearned > 0:
        cols[1].success(f"📥 {relearned} mot(s) réinjecté(s) dans votre file de révision SRS (rating = Faux).")

    corrected = correction.get("corrected_version", "")
    if corrected:
        st.markdown("#### Version corrigée")
        st.markdown(
            f'<div style="font-size: 1.5rem; line-height: 1.6; padding: 1rem; background: var(--ht-surface); border-radius: 10px;">{corrected}</div>',
            unsafe_allow_html=True,
        )
        pinyin = correction.get("pinyin", "")
        if pinyin:
            st.caption(f"Pinyin : {pinyin}")
        french = correction.get("french_translation", "")
        if french:
            st.caption(f"Traduction française : {french}")

    errors = correction.get("errors") or []
    if errors:
        st.markdown("#### Erreurs détectées")
        rows = []
        for err in errors:
            if not isinstance(err, dict):
                continue
            rows.append(
                {
                    "Type": err.get("type", ""),
                    "Segment": err.get("segment", ""),
                    "Correction": err.get("correction", ""),
                    "Explication": err.get("explanation", ""),
                }
            )
        if rows:
            st.table(rows)
    else:
        st.info("Aucune erreur détectée. Bravo !")

    strengths = correction.get("strengths") or []
    if strengths:
        st.markdown("#### Points forts")
        for strength in strengths:
            st.markdown(f"- {strength}")

    advice = correction.get("next_step_advice")
    if advice:
        st.markdown("#### Conseil pour progresser")
        st.markdown(advice)


def _render_history(user_id: int) -> None:
    attempts = list_expression_attempts(user_id, limit=10)
    if not attempts:
        return
    st.markdown("### Historique récent")
    for attempt in attempts:
        when = str(attempt.get("created_at", ""))[:19].replace("T", " ")
        with st.expander(f"HSK{attempt['hsk_level']} · score {attempt.get('score') or '?'} · {when}"):
            st.markdown(f"**Sujet :** {attempt.get('subject', '')}")
            st.markdown(f"**Votre texte :**")
            st.code(attempt.get("user_text", ""), language="text")
            correction = attempt.get("correction") or {}
            corrected = correction.get("corrected_version", "")
            if corrected:
                st.markdown(f"**Version corrigée :** {corrected}")
            errors = correction.get("errors") or []
            if errors:
                st.caption(f"{len(errors)} erreur(s) signalée(s).")


def main() -> None:
    st.set_page_config(page_title="Expression écrite", page_icon="✍️", layout="wide")
    _ensure_state()

    render_top_nav("expression")
    show_auth_notice()
    _render_intro()

    user = st.session_state.get("user")
    if not user:
        st.warning(
            "Connectez-vous pour utiliser la correction par IA. Cette page consomme des "
            "tokens Anthropic — l'accès est réservé aux comptes pour éviter les abus."
        )
        st.page_link("pages/Account.py", label="Se connecter / créer un compte")
        return

    if not llm.is_configured():
        st.error(
            "Aucune clé API Anthropic n'est configurée. Ajoutez `ANTHROPIC_API_KEY` "
            "dans `.streamlit/secrets.toml` ou en variable d'environnement, puis relancez."
        )
        return

    pool = st.session_state["expression_loaded_pool"]
    level = st.session_state["expression_level"]

    _render_configuration(pool)
    _render_generate_button(st.session_state["expression_level"])
    _render_subject_card()
    _render_writer(st.session_state["expression_level"], int(user["id"]))
    _render_correction()
    st.divider()
    _render_history(int(user["id"]))


if __name__ == "__main__":
    main()
