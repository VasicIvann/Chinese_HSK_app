"""Authentication and account related UI helpers."""

from __future__ import annotations

from typing import Dict, Iterable

import streamlit as st

from repo import authenticate_user, create_user, get_user_settings, update_user_locale
from utils.ui import trigger_rerun


SUPPORTED_LOCALES: Dict[str, str] = {
    "fr": "Francais",
    "en": "English",
}

PREFERENCE_LABELS: Dict[str, str] = {
    "default_num_questions": "Questions par quiz (defaut)",
}


def init_auth_state() -> None:
    """Ensure the authentication related keys exist in session state."""
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("user_settings", {})
    st.session_state.setdefault("auth_notice", None)


def show_auth_notice() -> None:
    """Display pending authentication flash messages."""
    notice = st.session_state.get("auth_notice")
    if not notice:
        return

    level, message = notice
    if level == "success":
        st.success(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)
    st.session_state["auth_notice"] = None


def _show_invalid_credentials(message: str) -> None:
    st.session_state["auth_notice"] = ("error", message)


def render_guest_forms() -> None:
    """Display login and sign-up forms for anonymous visitors."""
    tabs = st.tabs(["Connexion", "Creer un compte"])
    with tabs[0]:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Mot de passe", type="password", key="login_password")
            submit = st.form_submit_button("Se connecter")

        if submit:
            _process_login(email, password)

    with tabs[1]:
        with st.form("signup_form", clear_on_submit=False):
            email = st.text_input("Email *", key="signup_email")
            password = st.text_input("Mot de passe *", type="password", key="signup_password")
            confirm = st.text_input("Confirmer le mot de passe *", type="password", key="signup_confirm")
            locale_code = st.selectbox(
                "Langue de l'interface",
                options=list(SUPPORTED_LOCALES.keys()),
                format_func=lambda code: SUPPORTED_LOCALES[code],
                key="signup_locale",
            )
            submit = st.form_submit_button("Creer un compte")

        if submit:
            _process_signup(email, password, confirm, locale_code)

    st.caption("Continuer sans compte reste possible. Creez un compte pour sauvegarder vos preferences.")


def _process_login(email: str, password: str) -> None:
    if not email or not password:
        _show_invalid_credentials("Veuillez renseigner email et mot de passe.")
        return

    user = authenticate_user(email, password)
    if user is None:
        _show_invalid_credentials("Identifiants incorrects.")
        return

    st.session_state["user"] = user
    st.session_state["user_settings"] = get_user_settings(user["id"])
    st.session_state["auth_notice"] = ("success", "Connexion reussie. Preferences chargees.")
    trigger_rerun()


def _process_signup(email: str, password: str, confirm: str, locale_code: str) -> None:
    if not email or not password or not confirm:
        _show_invalid_credentials("Merci de remplir tous les champs obligatoires.")
        return
    if "@" not in email:
        _show_invalid_credentials("Adresse email invalide.")
        return
    if len(password) < 6:
        _show_invalid_credentials("Le mot de passe doit contenir au moins 6 caracteres.")
        return
    if password != confirm:
        _show_invalid_credentials("Les mots de passe ne correspondent pas.")
        return

    try:
        user = create_user(email, password, locale=locale_code)
    except ValueError as exc:
        _show_invalid_credentials(str(exc))
        return

    st.session_state["user"] = user
    st.session_state["user_settings"] = {}
    st.session_state["auth_notice"] = ("success", "Compte cree avec succes. Bienvenue !")
    trigger_rerun()


def render_account_overview() -> None:
    """Display the connected user details and stored preferences."""
    user = st.session_state.get("user")
    if user is None:
        render_guest_forms()
        return

    st.success(f"Connecte en tant que **{user['email']}**")

    locale_options: Iterable[str] = list(SUPPORTED_LOCALES.keys())
    current_locale = user.get("locale", "fr")
    if current_locale not in locale_options:
        locale_options = [current_locale, *locale_options]

    new_locale = st.selectbox(
        "Langue de l'interface",
        options=list(locale_options),
        index=list(locale_options).index(current_locale),
        format_func=lambda code: SUPPORTED_LOCALES.get(code, code),
        key="account_locale",
    )

    if new_locale != current_locale:
        update_user_locale(user["id"], new_locale)
        st.session_state["user"]["locale"] = new_locale
        st.session_state["auth_notice"] = ("success", "Langue mise a jour.")
        trigger_rerun()
        return

    st.write("Preferences enregistrees :")
    settings = st.session_state.get("user_settings", {})
    if not settings:
        st.info("Aucune preference enregistree pour le moment.")
    else:
        rows = []
        for key, value in settings.items():
            label = PREFERENCE_LABELS.get(key, key)
            display_value = value
            if value.isdigit():
                display_value = int(value)
            rows.append({"Preference": label, "Valeur": display_value})
        st.table(rows)

    if st.button("Se deconnecter", type="secondary"):
        handle_logout()


def handle_logout() -> None:
    """Clear authentication data from the session."""
    st.session_state["user"] = None
    st.session_state["user_settings"] = {}
    st.session_state["auth_notice"] = ("info", "Vous etes maintenant deconnecte.")
    trigger_rerun()


def ensure_user_settings_loaded() -> None:
    """Fetch persisted preferences for the current user if needed."""
    user = st.session_state.get("user")
    if user and not st.session_state.get("user_settings"):
        st.session_state["user_settings"] = get_user_settings(user["id"])
