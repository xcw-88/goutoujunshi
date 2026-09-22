from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    provider: str = "openai-compatible"
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    api_key_configured: bool
    api_key_masked: str | None


class SettingsUpdate(BaseModel):
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    clear_api_key: bool = False
    model: str | None = Field(default=None, min_length=1, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)

