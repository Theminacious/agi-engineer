"""Configuration management for V2 backend."""

from typing import Any, Dict, List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_FIELDS = (
    "github_app_private_key",
    "github_client_secret",
    "github_token",
    "jwt_secret_key",
    "webhook_secret",
    "groq_api_key",
    "database_url",
)

_REQUIRED_IN_PRODUCTION = (
    "jwt_secret_key",
    "webhook_secret",
    "github_client_secret",
    "github_app_private_key",
)

_PRODUCTION_ENVS = {"production", "prod", "staging"}

_MASK = "***REDACTED***"


class SettingsValidationError(RuntimeError):
    """Raised at startup when required secrets are missing in production."""


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Sensitive values must be provided through environment variables or .env.
    Never commit real credentials to version control. In production
    (``api_env`` in production/prod/staging) required secrets must be present
    and non-empty or startup fails closed.
    """

    github_app_id: int = 2623475
    github_app_private_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_token: Optional[str] = None

    database_url: str = "sqlite:///./agi_engineer_v2.db"

    redis_url: str = "redis://localhost:6379/0"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    frontend_url: str = "http://localhost:3000"

    jwt_secret_key: str = ""
    webhook_secret: str = ""

    groq_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.api_env.strip().lower() in _PRODUCTION_ENVS

    def missing_required_secrets(self) -> List[str]:
        """Required secret fields that are missing or empty."""
        missing: List[str] = []
        for field in _REQUIRED_IN_PRODUCTION:
            value = getattr(self, field, None)
            if value is None or str(value).strip() == "":
                missing.append(field)
        return missing

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "Settings":
        if self.is_production:
            missing = self.missing_required_secrets()
            if missing:
                raise SettingsValidationError(
                    "Refusing to start in environment "
                    f"'{self.api_env}': required secrets missing or empty: "
                    + ", ".join(sorted(missing))
                )
        return self

    def safe_dict(self) -> Dict[str, Any]:
        """Configuration with every secret field masked, safe to log."""
        data: Dict[str, Any] = {}
        for field in self.__class__.model_fields:
            value = getattr(self, field)
            if field in _SECRET_FIELDS and value not in (None, ""):
                data[field] = _MASK
            else:
                data[field] = value
        return data

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}={v!r}" for k, v in self.safe_dict().items())
        return f"Settings({inner})"

    __str__ = __repr__


settings = Settings()
