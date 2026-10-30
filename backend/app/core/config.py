"""Application settings.

Every value comes from the repository-root `.env` file. Missing required values
abort start-up instead of silently falling back to a default, so the running
process always reflects what the operator wrote down.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    app_base_url: str
    session_secret: str
    seller_email: str
    seller_password: str

    model_provider: str = "openai-compatible"
    model_base_url: str = ""
    model_api_key: str = ""
    model_name: str = ""
    model_timeout_seconds: float = 60.0

    paypal_env: str = "sandbox"
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_client_id: str = ""
    paypal_client_secret: str = ""

    @field_validator("session_secret")
    @classmethod
    def _session_secret_long_enough(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SESSION_SECRET must be at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def _postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        return value

    @field_validator("paypal_base_url")
    @classmethod
    def _sandbox_only(cls, value: str) -> str:
        if value.rstrip("/") not in {
            "https://api-m.sandbox.paypal.com",
            "https://api.sandbox.paypal.com",
        }:
            raise ValueError("PAYPAL_BASE_URL must point at the PayPal sandbox")
        return value.rstrip("/")

    @property
    def cookie_secure(self) -> bool:
        return urlparse(self.app_base_url).scheme == "https"

    @property
    def app_origin(self) -> str:
        parsed = urlparse(self.app_base_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
