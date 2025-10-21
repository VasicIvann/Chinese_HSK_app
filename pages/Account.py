"""Espace compte pour HSK Trainer."""

from __future__ import annotations

import streamlit as st

from seed import ensure_seeded
from utils.auth_ui import (
    ensure_user_settings_loaded,
    init_auth_state,
    render_account_overview,
    show_auth_notice,
)
from utils.ui import render_top_nav


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


if __name__ == "__main__":
    main()
