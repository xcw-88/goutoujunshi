"""Validate request-scoped attachments without writing them to cloud storage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from fastapi import HTTPException
from starlette.datastructures import UploadFile


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_TOTAL_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 12 * 1024 * 1024
MAX_FILES = 8
MAX_TEXT_CHARS = 100_000

MIME_BY_EXTENSION = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".json": {"application/json", "text/plain"},
    ".csv": {"text/csv", "application/csv", "text/plain"},
}
DEFAULT_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".txt": "text/plain", ".md": "text/markdown",
    ".json": "application/json", ".csv": "text/csv",
}


@dataclass(frozen=True)
class TransientFile:
    name: str
    extension: str
    mime_type: str
    content: bytes


def _valid_image(extension: str, content: bytes) -> bool:
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return True


async def read_upload(upload: UploadFile, *, text_only: bool = False) -> TransientFile:
    name = PurePath((upload.filename or "upload").replace("\\", "/")).name
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in MIME_BY_EXTENSION or (text_only and extension not in {".txt", ".md", ".json", ".csv"}):
        raise HTTPException(400, "unsupported file type")
    mime_type = (upload.content_type or "").lower()
    if mime_type in {"", "application/octet-stream"}:
        mime_type = DEFAULT_MIME[extension]
    if mime_type not in MIME_BY_EXTENSION[extension]:
        raise HTTPException(400, "unsupported file type")
    content = await upload.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "file exceeds 20 MB limit")
    if not _valid_image(extension, content):
        raise HTTPException(400, "invalid image content")
    return TransientFile(name=name, extension=extension, mime_type=mime_type, content=content)


async def read_uploads(uploads: list[UploadFile]) -> list[TransientFile]:
    if len(uploads) > MAX_FILES:
        raise HTTPException(400, "too many attachments")
    files = []
    total_size = 0
    image_size = 0
    for upload in uploads:
        item = await read_upload(upload)
        total_size += len(item.content)
        if item.mime_type.startswith("image/"):
            image_size += len(item.content)
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(413, "attachments exceed 20 MB total limit")
        if image_size > MAX_IMAGE_SIZE:
            raise HTTPException(413, "images exceed the 12 MB cloud model payload limit")
        files.append(item)
    return files
