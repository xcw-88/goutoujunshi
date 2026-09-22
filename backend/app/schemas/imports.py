from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ImportedLine(BaseModel):
    sender: str
    content: str
    timestamp: str | None = None


class ImportPreviewRequest(BaseModel):
    file_id: str


class ImportPreview(BaseModel):
    file_id: str
    format: str
    total_messages: int
    senders: list[str]
    preview: list[ImportedLine]
    mapping_required: bool = True


class ImportConfirmRequest(BaseModel):
    file_id: str
    user_sender: str = Field(min_length=1)
    object_sender: str = Field(min_length=1)
    person_id: str | None = None
    title: str = Field(default="导入的聊天记录", min_length=1, max_length=160)

    @model_validator(mode="after")
    def distinct_senders(self) -> ImportConfirmRequest:
        if self.user_sender == self.object_sender:
            raise ValueError("user_sender and object_sender must differ")
        return self


class ImportResult(BaseModel):
    conversation_id: str
    imported_messages: int

