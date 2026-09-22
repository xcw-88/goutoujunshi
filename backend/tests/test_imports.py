import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models import UploadedFile
from app.schemas.imports import ImportConfirmRequest
from app.services.import_service import ImportService


@pytest.mark.parametrize(
    ("name", "content", "expected_format"),
    [
        ("chat.txt", "[2026-01-01] 我: 你好\n小王: 嗨", "text"),
        ("chat.md", "- 我: 你好\n- 小王: 嗨", "markdown"),
        ("chat.csv", "sender,content,time\n我,你好,10:00\n小王,嗨,10:01", "csv"),
        ("chat.json", json.dumps([{"sender": "我", "text": "你好"}, {"sender": "小王", "text": "嗨"}]), "json"),
    ],
)
def test_preview_supported_formats(
    session: Session, tmp_path: Path, name: str, content: str, expected_format: str
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    record = UploadedFile(
        original_name=name,
        stored_name=name,
        mime_type="text/plain",
        size=path.stat().st_size,
        path=str(path),
    )
    session.add(record)
    session.commit()

    preview = ImportService(session).preview(record.id)
    assert preview.format == expected_format
    assert preview.senders == ["我", "小王"]
    assert preview.mapping_required is True


def test_confirm_requires_explicit_mapping_and_creates_transcript(
    session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "chat.txt"
    path.write_text("我: 你好\n小王: 嗨", encoding="utf-8")
    record = UploadedFile(
        original_name="chat.txt",
        stored_name="chat.txt",
        mime_type="text/plain",
        size=path.stat().st_size,
        path=str(path),
    )
    session.add(record)
    session.commit()

    conversation, count = ImportService(session).confirm(
        ImportConfirmRequest(
            file_id=record.id,
            user_sender="我",
            object_sender="小王",
            title="和小王的导入",
        )
    )
    assert count == 2
    assert "用户=我；对象=小王" in conversation.messages[0].content
    assert conversation.messages[0].metadata_json["type"] == "imported_chat"
