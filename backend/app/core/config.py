"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "CampaignX"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "campaignx"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Mock Campaign API
    MOCK_CAMPAIGN_API_URL: str = "https://mock-campaign-api.onrender.com"
    MOCK_API_TIMEOUT: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
