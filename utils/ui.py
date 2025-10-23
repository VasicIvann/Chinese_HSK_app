"""Streamlit UI utilities."""

from __future__ import annotations

from typing import Literal

import streamlit as st


TopNavPage = Literal["home", "account", "comprehension", "expression"]


def trigger_rerun() -> None:
    """Force a rerun compatible with both legacy and modern Streamlit."""
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return

    experimental_rerun = getattr(st, "experimental_rerun", None)
    if callable(experimental_rerun):
        experimental_rerun()
        return

    raise RuntimeError("Streamlit rerun API unavailable in this version.")


def inject_global_styles() -> None:
    """Apply a shared visual theme and hide the built-in sidebar navigation."""
    if st.session_state.get("_ui_styles_injected"):
        return

    st.session_state["_ui_styles_injected"] = True
    st.markdown(
        """
        <style>
            :root {
                --ht-primary: #1d4ed8;
                --ht-primary-dark: #1e3a8a;
                --ht-neutral: #0f172a;
                --ht-surface: rgba(255, 255, 255, 0.92);
                --ht-gradient: linear-gradient(135deg, #f8fafc 0%, #dbeafe 100%);
            }

            html, body, .stApp {
                background: var(--ht-gradient);
            }

            section[data-testid="stSidebar"],
            div[data-testid="stSidebarNav"],
            button[title="Menu"],
            button[aria-label="Menu"] {
                display: none !important;
            }

            header[data-testid="stHeader"] {
                background: transparent;
            }

            .block-container {
                max-width: 960px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }

            .block-container > div:first-child {
                position: sticky;
                top: 0;
                z-index: 1000;
                background: var(--ht-surface);
                backdrop-filter: blur(12px);
                border-radius: 999px;
                border: 1px solid rgba(15, 23, 42, 0.08);
                box-shadow: 0 18px 35px rgba(15, 23, 42, 0.08);
                margin-bottom: 2rem;
                padding: 0.45rem 1.25rem;
            }

            .block-container > div:first-child > div[data-testid="column"] {
                display: flex;
                align-items: center;
            }

            .block-container > div:first-child > div[data-testid="column"]:first-child {
                justify-content: flex-start;
            }

            .block-container > div:first-child > div[data-testid="column"]:last-child {
                justify-content: flex-end;
            }

            div[data-testid="stPageLink"] {
                width: auto !important;
            }

            div[data-testid="stPageLink"] button {
                border-radius: 999px;
                background: transparent;
                color: var(--ht-neutral);
                border: 1px solid transparent;
                font-weight: 600;
                font-size: 0.95rem;
                padding: 0.55rem 1rem;
                transition: all 0.2s ease;
            }

            div[data-testid="stPageLink"] button:hover {
                color: var(--ht-primary);
                border-color: rgba(37, 99, 235, 0.25);
                background: rgba(37, 99, 235, 0.08);
            }

            div[data-testid="stPageLink"] button:disabled,
            div[data-testid="stPageLink"] button:disabled:hover {
                background: var(--ht-primary);
                color: #ffffff;
                border-color: var(--ht-primary);
                cursor: default;
                box-shadow: 0 12px 22px rgba(29, 78, 216, 0.28);
            }

            button[data-testid="baseButton-primary"] {
                border-radius: 999px;
                padding: 0.75rem 2rem;
                font-size: 1rem;
                font-weight: 600;
                box-shadow: 0 18px 28px rgba(29, 78, 216, 0.25);
            }

            button[data-testid="baseButton-primary"]:hover {
                transform: translateY(-1px);
            }

            .stAlert {
                border-radius: 16px;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.75rem;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px;
                border: 1px solid transparent;
                padding: 0.45rem 1.25rem;
                font-weight: 600;
            }

            .hero-card {
                background: var(--ht-surface);
                border-radius: 26px;
                padding: 2.5rem;
                box-shadow: 0 30px 60px rgba(15, 23, 42, 0.16);
                margin-bottom: 1.75rem;
            }

            .hero-subtitle {
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--ht-primary-dark);
                margin-bottom: 0.5rem;
            }

            .hero-title {
                font-size: 2.25rem;
                font-weight: 700;
                color: var(--ht-neutral);
                margin-bottom: 0.75rem;
                line-height: 1.2;
            }

            .hero-text {
                font-size: 1.05rem;
                color: rgba(15, 23, 42, 0.8);
                max-width: 680px;
            }

            .feature-card {
                background: rgba(255, 255, 255, 0.85);
                border-radius: 22px;
                padding: 1.5rem;
                box-shadow: 0 18px 32px rgba(15, 23, 42, 0.12);
                height: 100%;
            }

            .feature-icon {
                font-size: 1.8rem;
                margin-bottom: 0.5rem;
            }

            .feature-card h3 {
                margin-bottom: 0.5rem;
                font-weight: 700;
                color: var(--ht-neutral);
            }

            .feature-card p {
                color: rgba(15, 23, 42, 0.78);
                font-size: 0.98rem;
            }

            .page-intro {
                background: var(--ht-surface);
                border-radius: 24px;
                padding: 1.75rem 2rem;
                box-shadow: 0 24px 44px rgba(15, 23, 42, 0.14);
                margin-bottom: 2.25rem;
            }

            .page-intro h1 {
                margin-bottom: 0.35rem;
                font-weight: 700;
                font-size: 2.05rem;
                color: var(--ht-neutral);
            }

            .page-intro p {
                margin: 0;
                color: rgba(15, 23, 42, 0.78);
                font-size: 1.05rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav(active_page: TopNavPage) -> None:
    """Display a sticky, minimal top navigation bar."""
    inject_global_styles()

    nav_cols = st.columns([1, 1])
    with nav_cols[0]:
        st.page_link(
            "Main.py",
            label="🏠 Accueil",
            help="Retourner a la page d'accueil",
            disabled=active_page == "home",
        )

    with nav_cols[1]:
        st.page_link(
            "pages/Account.py",
            label="👤 Compte",
            help="Gerer votre compte",
            disabled=active_page == "account",
        )
