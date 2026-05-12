"""Reusable FastAPI dependencies (auth, DB, quotas)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import JWTError, decode_access_token
from app.db.session import get_db
from app.models import User
from app.services.auth_service import get_user_by_id
from app.services.expression_service import get_daily_usage


bearer_scheme = HTTPBearer(auto_error=True)


DAILY_QUOTAS: dict[str, int] = {
    "expression_correction": 20,
    "subject_generation": 50,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and return the matching user, or raise 401."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sans sujet.",
        )
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sujet du token invalide.",
        ) from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )
    return user


def enforce_quota(kind: str):
    """Dependency factory: 429 when the user has hit today's quota for `kind`."""

    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        limit = DAILY_QUOTAS.get(kind, 0)
        if limit <= 0:
            return user
        usage = get_daily_usage(db, user.id, kind)
        if int(usage.count or 0) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Quota quotidien atteint pour '{kind}' "
                    f"({usage.count}/{limit}). Réessayez demain."
                ),
            )
        return user

    return _check


__all__ = ["DAILY_QUOTAS", "bearer_scheme", "enforce_quota", "get_current_user"]
