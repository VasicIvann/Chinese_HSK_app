"""Accueil modernise pour HSK Trainer."""

from __future__ import annotations

from typing import List, Tuple

import streamlit as st

from seed import ensure_seeded
from utils.auth_ui import init_auth_state, show_auth_notice
from utils.ui import render_top_nav, trigger_rerun


Feature = Tuple[str, str, str]

FEATURES: List[Feature] = [
    ("🧠", "Memorisation active", "Quiz adaptes par niveau pour revoir le vocabulaire cle des HSK 1 et 2."),
    ("🎯", "Parcours cible", "Choisissez rapidement le mode qui correspond a vos objectifs du moment."),
    ("📈", "Suivi personnel", "Sauvegardez vos preferences et revenez la ou vous vous etiez arrete."),
]


def _ensure_ui_state() -> None:
    init_auth_state()
    st.session_state.setdefault("show_training_modal", False)


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-subtitle">Votre coach HSK personnel</div>
            <h1 class="hero-title">Progressez en confiance sur la comprehension et l'expression ecrites</h1>
            <p class="hero-text">
                Lancez un entrainement personnalise, suivez vos progres et restez motive grace a une interface epuree.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cta_clicked = st.button(
        "Lancer un entrainement 🚀",
        type="primary",
        use_container_width=True,
        key="launch_training",
    )
    if cta_clicked:
        st.session_state["show_training_modal"] = True


def _render_features() -> None:
    st.markdown("### Ce que vous allez travailler")
    cols = st.columns(len(FEATURES))
    for col, (icon, title, description) in zip(cols, FEATURES):
        col.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_training_modal() -> None:
    if not st.session_state.get("show_training_modal"):
        return

    modal = getattr(st, "modal", None)
    if callable(modal):
        context_manager = modal("Choisissez votre parcours d'entrainement", key="training_modal")
    else:
        context_manager = st.container(border=True)

    with context_manager:
        if not callable(modal):
            st.subheader("Choisissez votre parcours d'entrainement")

        st.write(
            "Selectionnez l'axe qui correspond a votre objectif du moment. Vous pourrez changer a tout moment."
        )
        option_cols = st.columns(2)
        with option_cols[0]:
            st.page_link(
                "pages/01_Comprehension.py",
                label="📘 Comprehension ecrite",
                help="Quiz vocabulaire et comprehension rapide.",
            )
        with option_cols[1]:
            st.page_link(
                "pages/02_Expression.py",
                label="✍️ Expression ecrite",
                help="Travaillez vos productions redactionnelles.",
            )

        st.divider()
        close_kwargs = {"type": "secondary"}
        if not callable(modal):
            close_kwargs["use_container_width"] = True
        if st.button("Fermer", **close_kwargs):
            st.session_state["show_training_modal"] = False
            trigger_rerun()


def main() -> None:
    st.set_page_config(page_title="HSK Trainer", page_icon="📘", layout="wide")
    ensure_seeded()
    _ensure_ui_state()

    render_top_nav("home")
    show_auth_notice()

    _render_hero()
    _render_features()
    _render_training_modal()


if __name__ == "__main__":
    main()
