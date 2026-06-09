"""Application settings loaded from environment variables via pydantic-settings."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

import httpx
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """All application settings.

    Values are read from the environment (or a .env file).  Every field with no
    default **must** be set before the application starts.
    """

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "CampaignX API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── API ──────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server (default port)
        "http://localhost:8080",  # Vite dev server (configured port)
        "http://127.0.0.1:8080", # Vite via IPv4 loopback
        "http://localhost:3000",  # CRA / alternate dev
    ]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    # ── Database ─────────────────────────────────────────────────────
    # MONGODB_URL / MONGODB_DB_NAME: existing names kept for backward-compat
    # with mongodb.py.  MONGODB_URI / DATABASE_NAME are accepted aliases.
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_URI: str = ""          # when set, takes precedence over MONGODB_URL
    MONGODB_DB_NAME: str = "campaignx"
    DATABASE_NAME: str = ""        # when set, takes precedence over MONGODB_DB_NAME

    # ── AI Configuration (OpenRouter) ────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemini-2.5-flash-lite"

    # ── Mock Campaign API ─────────────────────────────────────────────
    MOCK_CAMPAIGN_API_URL: str = "https://mock-campaign-api.onrender.com"
    MOCK_API_TIMEOUT: int = 60      # seconds — handles cold starts
    MOCK_API_MAX_RETRIES: int = 3

    # ── Security ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # ── Derived / resolved properties ────────────────────────────────

    @model_validator(mode="after")
    def _resolve_aliases(self) -> "Settings":
        """Let the alias fields win when they are explicitly set."""
        if self.MONGODB_URI:
            self.MONGODB_URL = self.MONGODB_URI
        if self.DATABASE_NAME:
            self.MONGODB_DB_NAME = self.DATABASE_NAME
        return self

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_METHODS", "ALLOWED_HEADERS", mode="before")
    @classmethod
    def _parse_string_list(cls, v: Any) -> Any:
        """Accept both JSON array strings and comma-separated strings.

        DO App Platform injects env vars as raw strings, while .env files go
        through dotenv parsing. Both formats need to produce a list[str].
        """
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                import json as _json
                return _json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def _validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper

    # ── Connectivity validation helpers ──────────────────────────────

    async def validate_mongodb_connection(self) -> dict[str, Any]:
        """Ping MongoDB and return status info."""
        from motor.motor_asyncio import AsyncIOMotorClient  # lazy import
        try:
            client: AsyncIOMotorClient = AsyncIOMotorClient(
                self.MONGODB_URL,
                serverSelectionTimeoutMS=5_000,
                connectTimeoutMS=5_000,
            )
            await client.admin.command("ping")
            client.close()
            return {"status": "ok", "url": self.MONGODB_URL}
        except Exception as exc:
            logger.warning("MongoDB connectivity check failed: %s", exc)
            return {"status": "error", "detail": str(exc)}

    async def validate_llm_api_key(self) -> dict[str, Any]:
        """Test the OpenRouter API key with a lightweight models list call."""
        if not self.OPENROUTER_API_KEY:
            return {"status": "not_configured"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.OPENROUTER_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.OPENROUTER_API_KEY}"},
                )
            if resp.status_code == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.warning("OpenRouter API key check failed: %s", exc)
            return {"status": "error", "detail": str(exc)}

    async def validate_mock_api_connection(self) -> dict[str, Any]:
        """HEAD/GET the Mock Campaign API to check reachability."""
        try:
            async with httpx.AsyncClient(timeout=self.MOCK_API_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.MOCK_CAMPAIGN_API_URL}/api/customers/count"
                )
            return {"status": "ok", "http_status": resp.status_code}
        except Exception as exc:
            logger.warning("Mock Campaign API check failed: %s", exc)
            return {"status": "error", "detail": str(exc)}

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
