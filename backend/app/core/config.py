from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Process configuration loaded from environment variables and backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_base: str = Field("https://api.openai.com/v1", alias="GOUTOU_API_BASE")
    api_key: str = Field("", alias="GOUTOU_API_KEY")
    model: str = Field("gpt-4.1-mini", alias="GOUTOU_MODEL")
    temperature: float = Field(0.7, ge=0, le=2, alias="GOUTOU_TEMPERATURE")
    max_tokens: int = Field(1200, ge=1, le=32768, alias="GOUTOU_MAX_TOKENS")
    database_path: Path = Field(
        REPOSITORY_ROOT / "data" / "app.db", alias="GOUTOU_DATABASE_PATH"
    )
    upload_dir: Path = Field(
        REPOSITORY_ROOT / "data" / "uploads", alias="GOUTOU_UPLOAD_DIR"
    )

    def model_post_init(self, __context: object) -> None:
        if not self.database_path.is_absolute():
            self.database_path = (BACKEND_DIR / self.database_path).resolve()
        if not self.upload_dir.is_absolute():
            self.upload_dir = (BACKEND_DIR / self.upload_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()

