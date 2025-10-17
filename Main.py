"""Accueil de l'application HSK Trainer."""

from __future__ import annotations

import streamlit as st

from seed import ensure_seeded


def main() -> None:
    st.set_page_config(page_title="HSK Trainer", page_icon="🎓", layout="centered")
    ensure_seeded()

    st.title("HSK Trainer")
    st.caption("Plateforme d'entraînement multi-niveaux pour le vocabulaire et la compréhension HSK.")

    st.subheader("Choisissez votre domaine de travail")
    st.write(
        "L'application est organisée en deux axes principaux. Sélectionnez celui qui correspond à votre séance du jour."
    )

    st.page_link("pages/01_Comprehension.py", label="Compréhension écrite", help="Quiz vocabulaire et autres exercices de compréhension.")
    st.page_link("pages/02_Expression.py", label="Expression écrite", help="Bientôt disponible pour travailler la production.")

    st.divider()

    st.subheader("Fonctionnalités actuelles")
    st.write(
        "- Quiz de vocabulaire basés sur les listes officielles HSK 1 & 2\n"
        "- Choix dynamique du niveau et du nombre de questions\n"
        "- Suivi de session en cours"
    )

    st.subheader("Roadmap")
    st.write(
        "- Ajout d'autres modes de compréhension écrite inspirés des examens HSK\n"
        "- Création de comptes utilisateurs et suivi personnalisé\n"
        "- Personnalisation avec IA / machine learning\n"
        "- Extension multilingue de l'interface et des exercices"
    )


if __name__ == "__main__":
    main()
