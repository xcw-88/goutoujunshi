from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import Conversation, Message, Person, UploadedFile
from app.schemas.imports import ImportConfirmRequest, ImportedLine, ImportPreview


MAX_IMPORTED_MESSAGES = 5000
MAX_TRANSCRIPT_CHARS = 200_000
LINE_PATTERN = re.compile(
    r"^(?:\[(?P<timestamp>[^\]]+)\]\s*)?(?P<sender>[^:：]{1,80})[:：]\s*(?P<content>.+)$"
)


class ImportValidationError(ValueError):
    pass


class ImportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def preview(self, file_id: str) -> ImportPreview:
        record, lines, format_name = self._read(file_id)
        senders = list(dict.fromkeys(line.sender for line in lines if line.sender != "unknown"))
        return ImportPreview(
            file_id=record.id,
            format=format_name,
            total_messages=len(lines),
            senders=senders,
            preview=lines[:20],
        )

    def confirm(self, payload: ImportConfirmRequest) -> tuple[Conversation, int]:
        _, lines, _ = self._read(payload.file_id)
        senders = {line.sender for line in lines}
        if payload.user_sender not in senders or payload.object_sender not in senders:
            raise ImportValidationError("confirmed speakers must exist in the imported file")
        if payload.person_id and self.session.get(Person, payload.person_id) is None:
            raise ImportValidationError("person not found")
        selected = [
            line for line in lines if line.sender in {payload.user_sender, payload.object_sender}
        ]
        transcript_lines = []
        for line in selected:
            role = "用户" if line.sender == payload.user_sender else "对象"
            timestamp = f"[{line.timestamp}] " if line.timestamp else ""
            transcript_lines.append(f"{timestamp}{role}: {line.content}")
        transcript = "\n".join(transcript_lines)
        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n[记录因上下文限制已截断]"
        conversation = Conversation(title=payload.title, person_id=payload.person_id)
        conversation.messages.append(
            Message(
                role="user",
                content=(
                    "以下是用户已确认说话人映射的聊天记录。"
                    f"用户={payload.user_sender}；对象={payload.object_sender}。\n\n{transcript}"
                ),
                metadata_json={
                    "type": "imported_chat",
                    "file_id": payload.file_id,
                    "user_sender": payload.user_sender,
                    "object_sender": payload.object_sender,
                    "message_count": len(selected),
                },
            )
        )
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation, len(selected)

    def _read(self, file_id: str) -> tuple[UploadedFile, list[ImportedLine], str]:
        record = self.session.get(UploadedFile, file_id)
        if record is None:
            raise ImportValidationError("file not found")
        extension = Path(record.original_name).suffix.lower()
        if extension not in {".txt", ".md", ".json", ".csv"}:
            raise ImportValidationError("only TXT, Markdown, JSON, and CSV can be imported")
        try:
            text = Path(record.path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportValidationError("file must use UTF-8 encoding") from exc
        if extension == ".json":
            lines = self._parse_json(text)
            format_name = "json"
        elif extension == ".csv":
            lines = self._parse_csv(text)
            format_name = "csv"
        else:
            lines = self._parse_lines(text)
            format_name = "markdown" if extension == ".md" else "text"
        lines = [line for line in lines if line.content.strip()][:MAX_IMPORTED_MESSAGES]
        if not lines:
            raise ImportValidationError("no messages could be parsed")
        return record, lines, format_name

    @staticmethod
    def _parse_lines(text: str) -> list[ImportedLine]:
        parsed: list[ImportedLine] = []
        for raw in text.splitlines():
            line = raw.strip().lstrip("-* ")
            if not line:
                continue
            match = LINE_PATTERN.match(line)
            if match:
                parsed.append(ImportedLine(**match.groupdict()))
            else:
                parsed.append(ImportedLine(sender="unknown", content=line))
        return parsed

    @staticmethod
    def _parse_json(text: str) -> list[ImportedLine]:
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImportValidationError("invalid JSON") from exc
        if isinstance(payload, dict):
            payload = payload.get("messages", payload.get("data", []))
        if not isinstance(payload, list):
            raise ImportValidationError("JSON must be an array or contain messages")
        result = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            sender = item.get("sender") or item.get("from") or item.get("name")
            content = item.get("content") or item.get("text") or item.get("message")
            timestamp = item.get("timestamp") or item.get("time") or item.get("date")
            if sender is not None and content is not None:
                result.append(
                    ImportedLine(sender=str(sender), content=str(content), timestamp=str(timestamp) if timestamp else None)
                )
        return result

    @staticmethod
    def _parse_csv(text: str) -> list[ImportedLine]:
        reader = csv.DictReader(io.StringIO(text))
        result = []
        for item in reader:
            lowered = {str(key).lower(): value for key, value in item.items()}
            sender = lowered.get("sender") or lowered.get("from") or lowered.get("name")
            content = lowered.get("content") or lowered.get("text") or lowered.get("message")
            timestamp = lowered.get("timestamp") or lowered.get("time") or lowered.get("date")
            if sender and content:
                result.append(ImportedLine(sender=sender, content=content, timestamp=timestamp or None))
        return result

