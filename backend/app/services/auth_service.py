"""Authentication-related business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models import User


class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to register an email that already exists."""


class RegistrationNotAllowedError(Exception):
    """Raised when invite-only mode is enabled and the email isn't allowed."""


class InvalidCredentialsError(Exception):
    """Raised on bad email/password combinations."""


def register_user(db: Session, *, email: str, password: str, locale: str = "fr") -> User:
    """Create a new user account, enforcing invite-only mode if configured."""
    normalized_email = email.strip().lower()

    allowed = get_settings().allowed_registration_emails_set
    if allowed and normalized_email not in allowed:
        raise RegistrationNotAllowedError(
            "Cet email n'est pas autorisé à créer un compte sur cette instance."
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        locale=locale,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyRegisteredError("Email déjà enregistré.") from exc
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    """Return the user matching the credentials, or raise."""
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    user = db.execute(stmt).scalars().first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Identifiants incorrects.")
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
