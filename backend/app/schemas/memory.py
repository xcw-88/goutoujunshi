from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MemoryScope = Literal["user", "object", "relationship", "event", "hypothesis"]
MemorySource = Literal[
    "user_explicit", "user_report", "chatlab", "tool", "assistant_inference"
]
Confidence = Literal["high", "medium", "low"]


class MemoryInput(BaseModel):
    person_id: str | None = None
    scope: MemoryScope
    key: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=200)
    confidence: Confidence | None = None
    source: MemorySource = "user_explicit"
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def validate_semantics(self) -> MemoryInput:
        if self.scope == "user" and self.person_id is not None:
            raise ValueError("user scope must not be bound to a person")
        if self.scope != "user" and self.person_id is None:
            raise ValueError(f"{self.scope} scope requires person_id")
        if self.scope == "user" and self.source != "user_explicit":
            raise ValueError("user facts require user_explicit source")
        if self.scope in {"object", "relationship"} and self.source not in {
            "user_explicit",
            "user_report",
        }:
            raise ValueError("stable object and relationship facts require user input")
        if self.source in {"chatlab", "tool", "assistant_inference"} and self.scope not in {
            "event",
            "hypothesis",
        }:
            raise ValueError("tool and model output can only become events or hypotheses")
        if self.source == "assistant_inference" and self.scope != "hypothesis":
            raise ValueError("assistant inference can only become a hypothesis")
        if self.scope == "hypothesis" and self.confidence is None:
            raise ValueError("hypotheses require confidence")
        return self


class MemoryCreate(MemoryInput):
    pass


class MemoryUpdate(BaseModel):
    value: str | None = Field(default=None, min_length=1, max_length=200)
    confidence: Confidence | None = None
    source: MemorySource | None = None
    occurred_at: datetime | None = None


class MemoryRead(MemoryInput):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class MemoryContext(BaseModel):
    confirmed_facts: list[MemoryRead]
    events: list[MemoryRead]
    hypotheses: list[MemoryRead]

