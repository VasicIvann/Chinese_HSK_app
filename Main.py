"""Accueil de l'application HSK Trainer avec authentification basique."""

from __future__ import annotations

import streamlit as st

from repo import (
    authenticate_user,
    create_user,
    get_user_settings,
    set_user_setting,
    update_user_locale,
)
from seed import ensure_seeded
from utils.ui import trigger_rerun


SUPPORTED_LOCALES = {
    "fr": "Français",
    "en": "English",
}


def _init_session_state() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("user_settings", {})
    st.session_state.setdefault("auth_notice", None)


def _display_flash() -> None:
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


def _handle_login() -> None:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        submit = st.form_submit_button("Se connecter")

    if not submit:
        return

    if not email or not password:
        st.session_state["auth_notice"] = ("error", "Veuillez renseigner email et mot de passe.")
        return

    user = authenticate_user(email, password)
    if user is None:
        st.session_state["auth_notice"] = ("error", "Identifiants incorrects.")
        return

    st.session_state["user"] = user
    st.session_state["user_settings"] = get_user_settings(user["id"])
    st.session_state["auth_notice"] = ("success", "Connexion réussie. Vos préférences sont chargées.")
    trigger_rerun()


def _handle_signup() -> None:
    with st.form("signup_form", clear_on_submit=False):
        email = st.text_input("Email *", key="signup_email")
        password = st.text_input("Mot de passe *", type="password", key="signup_password")
        confirm = st.text_input("Confirmer le mot de passe *", type="password", key="signup_confirm")
        locale_label = st.selectbox(
            "Langue de l'interface",
            options=list(SUPPORTED_LOCALES.keys()),
            format_func=lambda code: SUPPORTED_LOCALES[code],
            key="signup_locale",
        )
        submit = st.form_submit_button("Créer un compte")

    if not submit:
        return

    if not email or not password or not confirm:
        st.session_state["auth_notice"] = ("error", "Merci de remplir tous les champs obligatoires.")
        return
    if "@" not in email:
        st.session_state["auth_notice"] = ("error", "Adresse email invalide.")
        return
    if len(password) < 6:
        st.session_state["auth_notice"] = ("error", "Le mot de passe doit contenir au moins 6 caractères.")
        return
    if password != confirm:
        st.session_state["auth_notice"] = ("error", "Les mots de passe ne correspondent pas.")
        return

    try:
        user = create_user(email, password, locale=locale_label)
    except ValueError as exc:
        st.session_state["auth_notice"] = ("error", str(exc))
        return

    st.session_state["user"] = user
    st.session_state["user_settings"] = {}
    st.session_state["auth_notice"] = ("success", "Compte créé avec succès. Bienvenue !")
    trigger_rerun()


def _handle_logout() -> None:
    st.session_state["user"] = None
    st.session_state["user_settings"] = {}
    st.session_state["auth_notice"] = ("info", "Vous êtes maintenant déconnecté.")
    trigger_rerun()


def _render_account_panel() -> None:
    user = st.session_state.get("user")
    if user is None:
        st.markdown("### Espace membre")
        tabs = st.tabs(["Connexion", "Créer un compte"])
        with tabs[0]:
            _handle_login()
        with tabs[1]:
            _handle_signup()
        st.caption(
            "Vous pouvez continuer en mode invité. Créez un compte pour sauvegarder vos préférences et vos progrès."
        )
        return

    st.markdown("### Compte")
    st.success(f"Connecté en tant que **{user['email']}**")

    current_locale = user.get("locale", "fr")
    locale_options = list(SUPPORTED_LOCALES.keys())
    if current_locale not in locale_options:
        locale_options.insert(0, current_locale)

    new_locale = st.selectbox(
        "Langue de l'interface",
        options=locale_options,
        index=locale_options.index(current_locale),
        format_func=lambda code: SUPPORTED_LOCALES.get(code, code),
        key="account_locale",
    )
    if new_locale != current_locale:
        update_user_locale(user["id"], new_locale)
        st.session_state["user"]["locale"] = new_locale
        st.session_state["auth_notice"] = ("success", "Langue mise à jour.")
        trigger_rerun()
        return

    st.write("Préférences enregistrées :")
    settings = st.session_state.get("user_settings", {})
    if not settings:
        st.info("Aucune préférence enregistrée pour le moment.")
    else:
        st.json(settings)

    if st.button("Se déconnecter", type="secondary"):
        _handle_logout()


def main() -> None:
    st.set_page_config(page_title="HSK Trainer", page_icon="🎓", layout="centered")
    ensure_seeded()
    _init_session_state()
    _display_flash()

    st.title("HSK Trainer")
    st.caption("Plateforme d'entraînement multi-niveaux pour le vocabulaire et la compréhension HSK.")

    st.subheader("Choisissez votre domaine de travail")
    st.write(
        "L'application est organisée en deux axes principaux. Sélectionnez celui qui correspond à votre séance du jour."
    )

    st.page_link(
        "pages/01_Comprehension.py",
        label="🧠 Compréhension écrite",
        help="Quiz vocabulaire et autres exercices de compréhension.",
    )
    st.page_link(
        "pages/02_Expression.py",
        label="✍️ Expression écrite",
        help="Bientôt disponible pour travailler la production.",
    )

    st.divider()

    left, right = st.columns((2, 1))

    with left:
        st.subheader("Fonctionnalités actuelles")
        st.write(
            "- Quiz de vocabulaire basés sur les listes officielles HSK 1 & 2\n"
            "- Choix dynamique du niveau et du nombre de questions\n"
            "- Suivi des sessions de quiz en cours"
        )

        st.subheader("Roadmap")
        st.write(
            "- Ajout d'autres modes de compréhension écrite inspirés des examens HSK\n"
            "- Création de comptes utilisateurs et suivi personnalisé\n"
            "- Personnalisation avec IA / machine learning\n"
            "- Extension multilingue de l'interface et des exercices"
        )

    with right:
        _render_account_panel()


if __name__ == "__main__":
    main()
