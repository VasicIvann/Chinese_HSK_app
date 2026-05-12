"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings, validated at boot via Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    HSK_DATABASE_URL: str = Field(
        default="sqlite:///./test.db",
        description="SQLAlchemy database URL.",
    )

    JWT_SECRET_KEY: str = Field(
        default="dev-only-change-me",
        min_length=8,
        description="Secret used to sign JWTs.",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_MINUTES: int = 43200  # 30 days

    ANTHROPIC_API_KEY: str = ""
    HSK_CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"

    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_REGISTRATION_EMAILS: str = ""

    @field_validator("HSK_DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        url = value.strip()
        if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_registration_emails_set(self) -> set[str]:
        raw = self.ALLOWED_REGISTRATION_EMAILS or ""
        return {email.strip().lower() for email in raw.split(",") if email.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
