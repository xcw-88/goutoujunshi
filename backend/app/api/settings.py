from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.settings_service import SettingsService


router = APIRouter(prefix="/api/settings", tags=["settings"])
Database = Annotated[Session, Depends(get_db)]
Configuration = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=SettingsRead)
def read_settings(db: Database, settings: Configuration) -> SettingsRead:
    return SettingsService(db, settings).read()


@router.patch("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate, db: Database, settings: Configuration
) -> SettingsRead:
    return SettingsService(db, settings).update(payload)

