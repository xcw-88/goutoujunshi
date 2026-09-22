from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    person_id: str | None = None
    message: str = Field(min_length=1, max_length=20_000)
    file_ids: list[str] = Field(default_factory=list, max_length=8)
    regenerate: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    intent: str
    risk: str
    references: list[str]
    usage: dict[str, int]
