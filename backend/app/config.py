"""Configuration management for V2 backend."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GitHub App
    github_app_id: int
    github_app_private_key: str
    github_client_id: str
    github_client_secret: str

    # Database
    database_url: str = "postgresql://localhost/agi_engineer_v2"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"

    # Security
    jwt_secret_key: str
    webhook_secret: str

    # AI
    groq_api_key: str

    # Frontend
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
