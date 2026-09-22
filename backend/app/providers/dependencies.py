from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.base import ModelProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.services.settings_service import SettingsService


def get_model_provider(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ModelProvider:
    values = SettingsService(db, settings).values()
    return OpenAICompatibleProvider(
        base_url=str(values["base_url"]),
        api_key=str(values["api_key"]),
        model=str(values["model"]),
        temperature=float(values["temperature"]),
        max_tokens=int(values["max_tokens"]),
    )
