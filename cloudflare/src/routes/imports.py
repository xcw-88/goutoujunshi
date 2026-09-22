from __future__ import annotations

import csv
import io
import json
import re

from fastapi import APIRouter, HTTPException, Request

from app.schemas.imports import ImportConfirmRequest, ImportedLine, ImportPreview, ImportPreviewRequest, ImportResult
from common import db, env, new_id, now


router = APIRouter(prefix="/api/imports", tags=["imports"])
MAX_IMPORTED_MESSAGES = 5000
MAX_TRANSCRIPT_CHARS = 200_000
LINE_PATTERN = re.compile(r"^(?:\[(?P<timestamp>[^\]]+)\]\s*)?(?P<sender>[^:：]{1,80})[:：]\s*(?P<content>.+)$")


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


async def _read(request: Request, file_id: str) -> tuple[list[ImportedLine], str]:
    record = await db(request).one("SELECT * FROM uploaded_files WHERE id = ?", file_id)
    if record is None:
        raise HTTPException(400, "file not found")
    extension = "." + record["original_name"].rsplit(".", 1)[-1].lower()
    if extension not in {".txt", ".md", ".json", ".csv"}:
        raise HTTPException(400, "only TXT, Markdown, JSON, and CSV can be imported")
    item = await env(request).UPLOADS.get(record["object_key"])
    if item is None:
        raise HTTPException(400, "file content not found")
    raw = await item.arrayBuffer()
    content = raw.to_bytes() if hasattr(raw, "to_bytes") else bytes(raw)
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


@router.post("/preview", response_model=ImportPreview)
async def preview_import(payload: ImportPreviewRequest, request: Request) -> ImportPreview:
    lines, format_name = await _read(request, payload.file_id)
    senders = list(dict.fromkeys(line.sender for line in lines if line.sender != "unknown"))
    return ImportPreview(
        file_id=payload.file_id, format=format_name, total_messages=len(lines),
        senders=senders, preview=lines[:20],
    )


@router.post("/confirm", response_model=ImportResult)
async def confirm_import(payload: ImportConfirmRequest, request: Request) -> ImportResult:
    lines, _ = await _read(request, payload.file_id)
    senders = {line.sender for line in lines}
    if payload.user_sender not in senders or payload.object_sender not in senders:
        raise HTTPException(400, "confirmed speakers must exist in the imported file")
    if payload.person_id and not await db(request).one("SELECT id FROM people WHERE id = ?", payload.person_id):
        raise HTTPException(400, "person not found")
    selected = [line for line in lines if line.sender in {payload.user_sender, payload.object_sender}]
    transcript_lines = []
    for line in selected:
        role = "用户" if line.sender == payload.user_sender else "对象"
        timestamp = f"[{line.timestamp}] " if line.timestamp else ""
        transcript_lines.append(f"{timestamp}{role}: {line.content}")
    transcript = "\n".join(transcript_lines)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n[记录因上下文限制已截断]"
    conversation_id, timestamp = new_id(), now()
    await db(request).batch([
        (
            "INSERT INTO conversations (id, title, person_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, payload.title, payload.person_id, timestamp, timestamp),
        ),
        (
            "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, 'user', ?, ?, ?)",
            (
                new_id(), conversation_id,
                f"以下是用户已确认说话人映射的聊天记录。用户={payload.user_sender}；对象={payload.object_sender}。\n\n{transcript}",
                json.dumps({
                    "type": "imported_chat", "file_id": payload.file_id,
                    "user_sender": payload.user_sender, "object_sender": payload.object_sender,
                    "message_count": len(selected),
                }, ensure_ascii=False),
                timestamp,
            ),
        ),
    ])
    return ImportResult(conversation_id=conversation_id, imported_messages=len(selected))
