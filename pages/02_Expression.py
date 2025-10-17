"""Page placeholder pour l'expression écrite."""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Expression écrite", page_icon="✍️", layout="centered")

    st.title("Expression écrite — Bientôt disponible")
    st.write(
        "Cette section proposera prochainement des exercices de rédaction, de correction et de feedback "
        "assistés par IA pour vous aider à progresser sur l'expression écrite du HSK."
    )

    st.info(
        "Au programme : dictées, productions guidées, correction automatique et entraînement ciblé sur vos faiblesses."
    )
    st.page_link("Main.py", label="⬅️ Retour à l'accueil")


if __name__ == "__main__":
    main()
