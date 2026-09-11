"""PromiseCheck Centralized Configuration (Twelve-Factor App compliant)."""

from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Environment & Process
    APP_ENV: str = "development"
    DEBUG: bool = False
    PUBLIC_APP_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"
    DEFAULT_TIMEZONE: str = "UTC"
    LOG_LEVEL: str = "INFO"

    # 2. CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 3. Security & Sessions
    SESSION_SIGNING_KEY: str = "dev-insecure-secret-key-change-me-32chars"
    SESSION_COOKIE_NAME: str = "promisecheck_session"
    SESSION_MAX_AGE_SECONDS: int = 604800  # 7 days

    # 4. Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/promisecheck"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/promisecheck"
    REDIS_URL: str = "redis://localhost:6379/0"

    # 5. Object Storage (S3 / MinIO)
    OBJECT_STORAGE_ENDPOINT: str = "http://localhost:9000"
    OBJECT_STORAGE_BUCKET: str = "promisecheck-artifacts"
    OBJECT_STORAGE_ACCESS_KEY: str = "minioadmin"
    OBJECT_STORAGE_SECRET_KEY: str = "minioadmin"

    # 6. AI & Language Models
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-3-5-sonnet-latest"
    LLM_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_RUN_COST_LIMIT: float = 1.00

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Enforce strict production safety checks."""
        if self.APP_ENV.lower() == "production":
            if (
                self.SESSION_SIGNING_KEY == "dev-insecure-secret-key-change-me-32chars"
                or len(self.SESSION_SIGNING_KEY) < 32
            ):
                raise ValueError(
                    "Unsafe production default: SESSION_SIGNING_KEY must be a secure "
                    "random string of at least 32 characters in production."
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "Unsafe production default: CORS_ORIGINS must not contain "
                    "wildcard '*' in production."
                )
        return self


settings = Settings()
