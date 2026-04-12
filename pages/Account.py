"""Espace compte pour HSK Trainer."""

from __future__ import annotations

import streamlit as st

from repo import get_user_mastery_entries, list_quizzes
from seed import ensure_seeded
from utils.auth_ui import (
    ensure_user_settings_loaded,
    init_auth_state,
    render_account_overview,
    show_auth_notice,
)
from utils.ui import render_top_nav


REVIEW_MAX_CONFIDENCE = 0.5
JUSTE_MIN_CONFIDENCE = 0.5
JUSTE_MAX_CONFIDENCE = 0.9
MASTERED_MIN_CONFIDENCE = 0.9


def _render_mastery_dashboard() -> None:
    """Show mastered vs review-needed words for the connected user."""
    user = st.session_state.get("user")
    if not user:
        st.info("Connectez-vous pour consulter vos mots maitrises et a revoir.")
        return

    quizzes = list_quizzes()
    quiz_options = ["ALL"] + [q["key"] for q in quizzes]
    quiz_titles = {q["key"]: q["title"] for q in quizzes}
    quiz_titles["ALL"] = "Tous les quiz"

    selected_quiz = st.selectbox(
        "Filtrer par quiz",
        options=quiz_options,
        format_func=lambda key: quiz_titles.get(key, key),
        key="account_mastery_quiz_filter",
    )

    rows = get_user_mastery_entries(
        user_id=int(user["id"]),
        quiz_key=None if selected_quiz == "ALL" else selected_quiz,
    )
    if not rows:
        st.caption("Aucune donnee de maitrise pour le moment. Faites quelques questions d'abord.")
        return

    mastered = [
        r for r in rows if float(r.get("confidence_score", 0.0) or 0.0) > MASTERED_MIN_CONFIDENCE
    ]
    juste = [
        r
        for r in rows
        if JUSTE_MIN_CONFIDENCE < float(r.get("confidence_score", 0.0) or 0.0) < JUSTE_MAX_CONFIDENCE
    ]
    review = [
        r for r in rows if float(r.get("confidence_score", 0.0) or 0.0) <= REVIEW_MAX_CONFIDENCE
    ]

    stats_cols = st.columns(4)
    stats_cols[0].metric("Total evalue", len(rows))
    stats_cols[1].metric("Maitrises", len(mastered))
    stats_cols[2].metric("Mots juste", len(juste))
    stats_cols[3].metric("A revoir", len(review))

    def to_table(source: list[dict]) -> list[dict]:
        return [
            {
                "Quiz": r.get("quiz_title"),
                "Hanzi": r.get("hanzi"),
                "Pinyin": r.get("pinyin"),
                "Traduction": r.get("translation"),
                "Statut": r.get("status"),
                "Confiance": round(float(r.get("confidence_score", 0.0)), 2),
                "Revisions": r.get("review_count"),
                "Derniere vue": str(r.get("last_seen_at", ""))[:19].replace("T", " "),
            }
            for r in source
        ]

    tabs = st.tabs(["Mots maitrises", "Mots juste", "Mots a revoir"])
    with tabs[0]:
        if mastered:
            st.dataframe(to_table(mastered), use_container_width=True, hide_index=True)
        else:
            st.caption("Aucun mot maitrise selon les reponses actuelles.")

    with tabs[1]:
        if juste:
            st.dataframe(to_table(juste), use_container_width=True, hide_index=True)
        else:
            st.caption("Aucun mot dans la zone intermediaire (0.5 < confiance < 0.9).")

    with tabs[2]:
        if review:
            st.dataframe(to_table(review), use_container_width=True, hide_index=True)
        else:
            st.caption("Aucun mot en difficulte pour l'instant.")


def main() -> None:
    st.set_page_config(page_title="Mon compte", page_icon="👤", layout="wide")
    ensure_seeded()
    init_auth_state()
    ensure_user_settings_loaded()

    render_top_nav("account")
    show_auth_notice()

    st.markdown(
        """
        <div class="page-intro">
            <h1>Votre espace personnel</h1>
            <p>Creez un compte ou connectez-vous pour sauvegarder vos preferences d'entrainement.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Gestion du compte")
    render_account_overview()

    st.markdown("### Mots maitrises / a revoir")
    _render_mastery_dashboard()


if __name__ == "__main__":
    main()
