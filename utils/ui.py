"""Streamlit UI utilities."""

from __future__ import annotations

import streamlit as st


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
