"""Application settings, read from environment variables or a .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/roadwatch"
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 60
    upload_dir: Path = Path("uploads")
    max_photo_bytes: int = 5 * 1024 * 1024
    submissions_per_hour: int = 10
    text_classifier_path: Path = Path(__file__).resolve().parents[1] / "ai" / "artifacts" / "text_classifier.joblib"
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None  # a model name from: python -m app.cli.try_llm --list-models
    gemini_thinking_level: str | None = None  # for example low or minimal; empty means the model's default
    llm_timeout_seconds: float = 30
    timezone: str = "Asia/Karachi"  # the day boundaries administrators see in date filters
    triage_max_tool_calls: int = 5
    triage_timeout_seconds: int = 20
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
