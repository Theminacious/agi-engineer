"""Configuration management for V2 backend."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Sensitive values should be provided through environment variables or .env.
    Never commit real credentials to version control.
    """

    # GitHub App
    github_app_id: int = 2623475
    github_app_private_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_token: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./agi_engineer_v2.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    frontend_url: str = "http://localhost:3000"

    # Security
    jwt_secret_key: str = ""
    webhook_secret: str = ""

    # AI
    groq_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()