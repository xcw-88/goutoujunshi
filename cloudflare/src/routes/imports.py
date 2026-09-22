from __future__ import annotations

import csv
import io
import json
import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.schemas.imports import ImportedLine, ImportResult
from common import db, new_id, now
from transient_files import read_upload


router = APIRouter(prefix="/api/imports", tags=["imports"])
MAX_IMPORTED_MESSAGES = 5000
MAX_TRANSCRIPT_CHARS = 200_000
LINE_PATTERN = re.compile(r"^(?:\[(?P<timestamp>[^\]]+)\]\s*)?(?P<sender>[^:：]{1,80})[:：]\s*(?P<content>.+)$")


class CloudImportConfirm(BaseModel):
    user_sender: str = Field(min_length=1)
    object_sender: str = Field(min_length=1)
    person_id: str | None = None
    title: str = Field(default="导入的聊天记录", min_length=1, max_length=160)

    @model_validator(mode="after")
    def distinct_senders(self) -> "CloudImportConfirm":
        if self.user_sender == self.object_sender:
            raise ValueError("speakers must differ")
        return self


def _parse_lines(text: str) -> list[ImportedLine]:
    result = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-* ")
        if line:
            match = LINE_PATTERN.match(line)
            result.append(ImportedLine(**match.groupdict()) if match else ImportedLine(sender="unknown", content=line))
    return result


def _parse_json(text: str) -> list[ImportedLine]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "invalid JSON") from exc
    if isinstance(payload, dict):
        payload = payload.get("messages", payload.get("data", []))
    if not isinstance(payload, list):
        raise HTTPException(400, "JSON must be an array or contain messages")
    result = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        sender = item.get("sender") or item.get("from") or item.get("name")
        content = item.get("content") or item.get("text") or item.get("message")
        timestamp = item.get("timestamp") or item.get("time") or item.get("date")
        if sender is not None and content is not None:
            result.append(ImportedLine(sender=str(sender), content=str(content), timestamp=str(timestamp) if timestamp else None))
    return result


def _parse_csv(text: str) -> list[ImportedLine]:
    result = []
    for item in csv.DictReader(io.StringIO(text)):
        lowered = {str(key).lower(): value for key, value in item.items()}
        sender = lowered.get("sender") or lowered.get("from") or lowered.get("name")
        content = lowered.get("content") or lowered.get("text") or lowered.get("message")
        timestamp = lowered.get("timestamp") or lowered.get("time") or lowered.get("date")
        if sender and content:
            result.append(ImportedLine(sender=sender, content=content, timestamp=timestamp or None))
    return result


async def _read(upload: UploadFile) -> tuple[list[ImportedLine], str]:
    item = await read_upload(upload, text_only=True)
    extension, content = item.extension, item.content
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "file must use UTF-8 encoding") from exc
    if extension == ".json":
        lines, format_name = _parse_json(text), "json"
    elif extension == ".csv":
        lines, format_name = _parse_csv(text), "csv"
    else:
        lines, format_name = _parse_lines(text), "markdown" if extension == ".md" else "text"
    lines = [line for line in lines if line.content.strip()][:MAX_IMPORTED_MESSAGES]
    if not lines:
        raise HTTPException(400, "no messages could be parsed")
    return lines, format_name


@router.post("/preview")
async def preview_import(file: UploadFile = File(...)) -> dict:
    lines, format_name = await _read(file)
    senders = list(dict.fromkeys(line.sender for line in lines if line.sender != "unknown"))
    return {"format": format_name, "total_messages": len(lines), "senders": senders,
            "preview": [line.model_dump() for line in lines[:20]], "mapping_required": True}


@router.post("/confirm", response_model=ImportResult)
async def confirm_import(request: Request, file: UploadFile = File(...), payload: str = Form(...)) -> ImportResult:
    try:
        details = CloudImportConfirm.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(422, "invalid import confirmation") from exc
    lines, _ = await _read(file)
    senders = {line.sender for line in lines}
    if details.user_sender not in senders or details.object_sender not in senders:
        raise HTTPException(400, "confirmed speakers must exist in the imported file")
    if details.person_id and not await db(request).one("SELECT id FROM people WHERE id = ?", details.person_id):
        raise HTTPException(400, "person not found")
    selected = [line for line in lines if line.sender in {details.user_sender, details.object_sender}]
    transcript_lines = []
    for line in selected:
        role = "用户" if line.sender == details.user_sender else "对象"
        timestamp = f"[{line.timestamp}] " if line.timestamp else ""
        transcript_lines.append(f"{timestamp}{role}: {line.content}")
    transcript = "\n".join(transcript_lines)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n[记录因上下文限制已截断]"
    conversation_id, timestamp = new_id(), now()
    await db(request).batch([
        (
            "INSERT INTO conversations (id, title, person_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, details.title, details.person_id, timestamp, timestamp),
        ),
        (
            "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, 'user', ?, ?, ?)",
            (
                new_id(), conversation_id,
                f"以下是用户已确认说话人映射的聊天记录。用户={details.user_sender}；对象={details.object_sender}。\n\n{transcript}",
                json.dumps({
                    "type": "imported_chat",
                    "user_sender": details.user_sender, "object_sender": details.object_sender,
                    "message_count": len(selected),
                }, ensure_ascii=False),
                timestamp,
            ),
        ),
    ])
    return ImportResult(conversation_id=conversation_id, imported_messages=len(selected))
