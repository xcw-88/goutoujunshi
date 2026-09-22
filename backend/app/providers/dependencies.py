from __future__ import annotations

from app.core.config import get_settings
from app.providers.base import ModelProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


def get_model_provider() -> ModelProvider:
    settings = get_settings()
    return OpenAICompatibleProvider(
        base_url=settings.api_base,
        api_key=settings.api_key,
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

