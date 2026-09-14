"""PromiseCheck Centralized Configuration (Twelve-Factor App compliant)."""

from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
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

    # 3. Security, JWT & Tokens
    SECRET_KEY: str = ""
    JWT_SECRET_KEY: str = ""
    SESSION_SIGNING_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_COOKIE_NAME: str = "promisecheck_refresh"
    ACCESS_COOKIE_NAME: str = "promisecheck_access"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    GOOGLE_CLIENT_ID: str = ""

    # 4. Database & Cache
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""
    REDIS_URL: str = ""

    # 5. AI, Groq & Extraction
    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""
    LLM_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_RUN_COST_LIMIT: float = 1.00

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Enforce strict production safety checks."""
        if self.APP_ENV.lower() == "production":
            sec_key = self.SESSION_SIGNING_KEY if self.SESSION_SIGNING_KEY else self.JWT_SECRET_KEY
            if (
                not sec_key
                or sec_key in ("dev-insecure-secret-key-change-me-32chars", "dev-insecure-jwt-secret-key-change-me-32chars")
                or len(sec_key) < 32
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
