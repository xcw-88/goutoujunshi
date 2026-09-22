from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    stored_name: str
    mime_type: str
    size: int
    created_at: datetime

