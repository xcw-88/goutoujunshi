from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=4000)


class PersonUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)


class RelationshipWrite(BaseModel):
    status: str = Field(default="unknown", min_length=1, max_length=64)
    notes: str = Field(default="", max_length=4000)


class RelationshipRead(RelationshipWrite):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_id: str
    created_at: datetime
    updated_at: datetime


class PersonRead(PersonCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    relationship_profile: RelationshipRead | None = None

