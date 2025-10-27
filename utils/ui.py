"""Streamlit UI utilities."""

from __future__ import annotations

from typing import Literal

import streamlit as st
from streamlit.components.v1 import html as components_html


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
    if not st.session_state.get("_ui_styles_injected"):
        st.session_state["_ui_styles_injected"] = True
        st.markdown(
        """
        <style>
            :root {
                --ht-bg: #0b1120;
                --ht-surface: #111827;
                --ht-surface-alt: #0f172a;
                --ht-card: #1f2937;
                --ht-border: rgba(148, 163, 184, 0.16);
                --ht-text: #e2e8f0;
                --ht-muted: #94a3b8;
                --ht-primary: #ef4444;
                --ht-primary-hover: #f87171;
            }

            html, body, .stApp {
                background: var(--ht-bg);
                color: var(--ht-text);
            }

            .stApp {
                min-height: 100vh;
            }

            body.ht-modal-open {
                overflow: hidden;
            }

            body.ht-modal-open::before {
                content: "";
                position: fixed;
                inset: 0;
                background: rgba(8, 15, 35, 0.7);
                backdrop-filter: blur(6px);
                z-index: 998;
            }

            .ht-modal-fallback {
                position: fixed !important;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
                z-index: 999;
                pointer-events: none;
            }

            .ht-modal-fallback > div {
                width: min(520px, 100%);
                pointer-events: auto;
            }

            .ht-modal-fallback [data-testid="stVerticalBlock"] {
                width: 100%;
            }

            .ht-modal-fallback [data-testid="stVerticalBlock"] > div {
                background: rgba(17, 24, 39, 0.95);
                border-radius: 24px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 36px 85px rgba(8, 15, 35, 0.62);
                padding: 2rem;
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
                max-width: 1080px;
                padding: 2rem 1.5rem 4rem;
            }

            .block-container > div:first-child {
                position: sticky;
                top: 0;
                z-index: 1000;
                background: rgba(8, 15, 35, 0.82);
                backdrop-filter: blur(18px);
                border-radius: 999px;
                border: 1px solid var(--ht-border);
                box-shadow: 0 24px 48px rgba(8, 15, 35, 0.45);
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
                color: var(--ht-muted);
                border: 1px solid transparent;
                font-weight: 600;
                font-size: 0.95rem;
                padding: 0.55rem 1rem;
                transition: all 0.2s ease;
            }

            div[data-testid="stPageLink"] button:hover {
                color: var(--ht-text);
                border-color: rgba(248, 250, 252, 0.18);
                background: rgba(248, 250, 252, 0.08);
            }

            div[data-testid="stPageLink"] button:disabled,
            div[data-testid="stPageLink"] button:disabled:hover {
                background: var(--ht-primary);
                color: #0b1120;
                border-color: transparent;
                cursor: default;
                box-shadow: 0 18px 38px rgba(239, 68, 68, 0.35);
            }

            button[data-testid="baseButton-primary"] {
                border-radius: 999px;
                padding: 0.75rem 2rem;
                font-size: 1rem;
                font-weight: 600;
                box-shadow: 0 22px 32px rgba(239, 68, 68, 0.35);
                background: var(--ht-primary);
                border: 1px solid transparent;
                color: #0b1120;
            }

            button[data-testid="baseButton-primary"]:hover {
                background: var(--ht-primary-hover);
                transform: translateY(-1px);
            }

            button[data-testid="baseButton-secondary"] {
                border-radius: 999px;
                padding: 0.7rem 2rem;
                font-size: 0.95rem;
                font-weight: 600;
                border: 1px solid var(--ht-border);
                background: rgba(15, 23, 42, 0.6);
                color: var(--ht-text);
                box-shadow: 0 12px 25px rgba(8, 15, 35, 0.32);
            }

            button[data-testid="baseButton-secondary"]:hover {
                border-color: rgba(148, 163, 184, 0.45);
                background: rgba(15, 23, 42, 0.75);
            }

            .stAlert {
                border-radius: 16px;
                background: rgba(15, 23, 42, 0.75);
                border: 1px solid var(--ht-border);
                color: var(--ht-text);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.75rem;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px;
                border: 1px solid transparent;
                padding: 0.45rem 1.25rem;
                font-weight: 600;
                background: rgba(15, 23, 42, 0.65);
                color: var(--ht-muted);
            }

            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background: var(--ht-primary);
                color: #0b1120;
            }

            .hero-card {
                background: linear-gradient(145deg, rgba(17, 24, 39, 0.96), rgba(15, 23, 42, 0.9));
                border-radius: 26px;
                padding: 2.5rem;
                box-shadow: 0 34px 70px rgba(8, 15, 35, 0.55);
                margin-bottom: 1.9rem;
                border: 1px solid rgba(148, 163, 184, 0.12);
            }

            .hero-subtitle {
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--ht-muted);
                margin-bottom: 0.5rem;
            }

            .hero-title {
                font-size: 2.4rem;
                font-weight: 700;
                color: #f8fafc;
                margin-bottom: 0.75rem;
                line-height: 1.25;
            }

            .hero-text {
                font-size: 1.05rem;
                color: var(--ht-muted);
                max-width: 680px;
            }

            .feature-card {
                background: rgba(17, 24, 39, 0.92);
                border-radius: 22px;
                padding: 1.5rem;
                box-shadow: 0 24px 58px rgba(8, 15, 35, 0.45);
                height: 100%;
                border: 1px solid rgba(148, 163, 184, 0.14);
            }

            .feature-icon {
                font-size: 1.8rem;
                margin-bottom: 0.6rem;
            }

            .feature-card h3 {
                margin-bottom: 0.5rem;
                font-weight: 700;
                color: #f8fafc;
            }

            .feature-card p {
                color: var(--ht-muted);
                font-size: 0.98rem;
            }

            .page-intro {
                background: rgba(15, 23, 42, 0.88);
                border-radius: 24px;
                padding: 1.75rem 2rem;
                box-shadow: 0 28px 60px rgba(8, 15, 35, 0.48);
                margin-bottom: 2.25rem;
                border: 1px solid rgba(148, 163, 184, 0.12);
            }

            .page-intro h1 {
                margin-bottom: 0.4rem;
                font-weight: 700;
                font-size: 2.15rem;
                color: #f8fafc;
            }

            .page-intro p {
                margin: 0;
                color: var(--ht-muted);
                font-size: 1.05rem;
            }

            div[data-testid="stMetricValue"] {
                color: #f8fafc;
            }

            div[data-testid="stMetricLabel"] > span {
                color: var(--ht-muted);
            }

            div[data-testid="stModal"] {
                background: rgba(8, 15, 35, 0.65);
                backdrop-filter: blur(6px);
            }

            div[data-testid="stModalContent"] {
                background: rgba(17, 24, 39, 0.95);
                border-radius: 24px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 36px 85px rgba(8, 15, 35, 0.62);
                color: var(--ht-text);
                padding: 2rem 2.25rem;
            }

            div[data-testid="stModal"] h2,
            div[data-testid="stModal"] p {
                color: inherit;
            }

            div[data-testid="stModal"] div[data-testid="stMetricValue"] {
                color: inherit;
            }

            div[data-testid="stModalContent"] div[data-testid="column"] div[data-testid="stPageLink"] button {
                width: 100%;
                border-radius: 16px;
                padding: 0.85rem 1.25rem;
                font-weight: 600;
                font-size: 1rem;
                border: 1px solid rgba(148, 163, 184, 0.22);
                background: rgba(15, 23, 42, 0.75);
                color: #f8fafc;
                box-shadow: 0 18px 40px rgba(8, 15, 35, 0.5);
            }

            div[data-testid="stModalContent"] div[data-testid="column"] div[data-testid="stPageLink"] button:hover {
                border-color: rgba(148, 163, 184, 0.4);
                background: rgba(15, 23, 42, 0.9);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    components_html(
        """
        <script>
        const doc = window.parent?.document;
        if (!doc) {
            return;
        }
        doc.querySelectorAll('.ht-modal-fallback').forEach((el) => el.classList.remove('ht-modal-fallback'));
        doc.querySelectorAll('.ht-modal-card').forEach((el) => el.classList.remove('ht-modal-card'));
        const body = doc.body;
        if (body) {
            body.classList.remove('ht-modal-open');
        }
        </script>
        """,
        height=0,
    )


def render_top_nav(active_page: TopNavPage) -> None:
    """Display a sticky, minimal top navigation bar."""
    inject_global_styles()
    if active_page != "home":
        st.session_state["show_training_modal"] = False

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
