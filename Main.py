"""Accueil modernise pour HSK Trainer."""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import streamlit as st
from streamlit.components.v1 import html as components_html

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


def _set_modal_dom_state(active: bool) -> None:
    """Toggle DOM classes that emulate a modal when the native API is unavailable."""
    flag = "true" if active else "false"
    components_html(
        f"""
        <script>
        const doc = window.parent?.document;
        if (!doc) {{
            return;
        }}
        const body = doc.body;
        if (body) {{
            body.classList.remove('ht-modal-open');
            if ({flag}) {{
                body.classList.add('ht-modal-open');
            }}
        }}

        doc.querySelectorAll('.ht-modal-fallback').forEach((el) => el.classList.remove('ht-modal-fallback'));
        doc.querySelectorAll('.ht-modal-card').forEach((el) => el.classList.remove('ht-modal-card'));

        if (!({flag})) {{
            return;
        }}

        const blocks = doc.querySelectorAll('section.main .block-container > div[data-testid="stVerticalBlock"]');
        if (!blocks.length) {{
            return;
        }}
        const target = blocks[blocks.length - 1];
        target.classList.add('ht-modal-fallback');
        const inner = target.querySelector('div[data-testid="stVerticalBlock"]');
        if (inner) {{
            inner.classList.add('ht-modal-card');
        }}
        </script>
        """,
        height=0,
    )


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



def _render_training_modal_body(
    close_button_full_width: bool,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    st.write("Choisissez l'etape suivante pour poursuivre votre entrainement.")
    option_cols = st.columns(3)
    with option_cols[0]:
        st.page_link(
            "pages/01_Comprehension.py",
            label="Comprehension ecrite",
            help="Quiz vocabulaire et comprehension rapide.",
        )
    with option_cols[1]:
        st.page_link(
            "pages/02_Expression.py",
            label="Expression ecrite",
            help="Travaillez vos productions redactionnelles.",
        )
    with option_cols[2]:
        button_kwargs = {"type": "secondary"}
        if close_button_full_width:
            button_kwargs["use_container_width"] = True
        if st.button("Accueil", **button_kwargs):
            if on_close:
                on_close()
            st.session_state["show_training_modal"] = False
            trigger_rerun()


def _render_training_modal() -> None:
    if not st.session_state.get("show_training_modal"):
        _set_modal_dom_state(False)
        return

    modal = getattr(st, "modal", None)
    if callable(modal):
        _set_modal_dom_state(False)
        with modal("Choisissez votre parcours d'entrainement", key="training_modal"):
            _render_training_modal_body(close_button_full_width=True)
        return

    fallback_shell = st.container()
    with fallback_shell:
        card = st.container()
        with card:
            st.subheader("Choisissez votre parcours d'entrainement")
            _render_training_modal_body(
                close_button_full_width=True,
                on_close=lambda: _set_modal_dom_state(False),
            )

    _set_modal_dom_state(True)


def main() -> None:
    st.set_page_config(page_title="HSK Trainer", page_icon="📘", layout="wide")
    ensure_seeded()
    _ensure_ui_state()

    render_top_nav("home")

    if st.session_state.get("show_training_modal"):
        _render_training_modal()
        return

    show_auth_notice()

    _render_hero()
    _render_features()
    _render_training_modal()


if __name__ == "__main__":
    main()


