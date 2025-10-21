"""Apercu de la future section expression ecrite."""

from __future__ import annotations

import streamlit as st

from utils.auth_ui import init_auth_state, show_auth_notice
from utils.ui import render_top_nav


HIGHLIGHTS = [
    ("📝", "Ateliers guides", "Des sujets inspires des epreuves officielles avec accompagnement pas a pas."),
    ("🤖", "Feedback intelligent", "Analyse automatique de vos productions pour cibler les points a renforcer."),
    ("🤝", "Collaboration", "Correction croisee et partage des meilleures pratiques avec la communaute."),
]


def main() -> None:
    st.set_page_config(page_title="Expression ecrite", page_icon="✍️", layout="wide")
    init_auth_state()

    render_top_nav("expression")
    show_auth_notice()

    st.markdown(
        """
        <div class="page-intro">
            <h1>Expression ecrite</h1>
            <p>Une experience dediee a la production ecrite HSK arrive bientot. Restez a l'ecoute !</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Ce qui se prepare")
    cols = st.columns(len(HIGHLIGHTS))
    for col, (icon, title, description) in zip(cols, HIGHLIGHTS):
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

    st.info(
        "Envie d'entrainement immediat ? Relancez un quiz de comprehension ecrite depuis la page d'accueil."
    )


if __name__ == "__main__":
    main()
