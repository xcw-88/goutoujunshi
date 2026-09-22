from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UploadedFile


MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".json", ".csv"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/csv",
}


class FileValidationError(ValueError):
    pass


class FileNotFoundError(LookupError):
    pass


class FileService:
    def __init__(self, session: Session, upload_dir: Path) -> None:
        self.session = session
        self.upload_dir = upload_dir.resolve()

    def list(self) -> list[UploadedFile]:
        return list(self.session.scalars(select(UploadedFile).order_by(UploadedFile.created_at.desc())))

    def get(self, file_id: str) -> UploadedFile:
        record = self.session.get(UploadedFile, file_id)
        if record is None:
            raise FileNotFoundError(file_id)
        return record

    async def save(self, upload: UploadFile) -> UploadedFile:
        original_name = Path(upload.filename or "upload").name
        extension = Path(original_name).suffix.lower()
        mime_type = (upload.content_type or "application/octet-stream").lower()
        if extension not in ALLOWED_EXTENSIONS or mime_type not in ALLOWED_MIME_TYPES:
            raise FileValidationError("unsupported file type")
        content = await upload.read(MAX_UPLOAD_SIZE + 1)
        if len(content) > MAX_UPLOAD_SIZE:
            raise FileValidationError("file exceeds 20 MB limit")
        stored_name = f"{uuid.uuid4().hex}{extension}"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        target = (self.upload_dir / stored_name).resolve()
        if not target.is_relative_to(self.upload_dir):
            raise FileValidationError("invalid file path")
        target.write_bytes(content)
        record = UploadedFile(
            original_name=original_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size=len(content),
            path=str(target),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete(self, file_id: str) -> None:
        record = self.get(file_id)
        target = Path(record.path).resolve()
        if target.is_relative_to(self.upload_dir) and target.exists():
            target.unlink()
        self.session.delete(record)
        self.session.commit()

