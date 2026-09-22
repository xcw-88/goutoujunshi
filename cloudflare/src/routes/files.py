from __future__ import annotations

from pathlib import PurePath
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status

from app.schemas.file import FileRead
from common import db, env, new_id, now, require


router = APIRouter(prefix="/api/files", tags=["files"])
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".json", ".csv"}
ALLOWED_MIME_TYPES = {
    "image/png", "image/jpeg", "image/webp", "text/plain", "text/markdown",
    "application/json", "text/csv", "application/csv",
}


async def _get(request: Request, file_id: str) -> dict:
    return require(await db(request).one("SELECT * FROM uploaded_files WHERE id = ?", file_id), "file")


@router.get("", response_model=list[FileRead])
async def list_files(request: Request) -> list[dict]:
    return await db(request).all("SELECT * FROM uploaded_files ORDER BY created_at DESC")


@router.post("", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(request: Request, file: UploadFile = File(...)) -> dict:
    original_name = PurePath((file.filename or "upload").replace("\\", "/")).name
    extension = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    mime_type = (file.content_type or "application/octet-stream").lower()
    if extension not in ALLOWED_EXTENSIONS or mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "unsupported file type")
    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, "file exceeds 20 MB limit")
    file_id = new_id()
    stored_name = file_id + extension
    object_key = "uploads/" + stored_name
    await env(request).UPLOADS.put(object_key, content)
    try:
        await db(request).run(
            """INSERT INTO uploaded_files
            (id, original_name, stored_name, mime_type, size, object_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            file_id, original_name, stored_name, mime_type, len(content), object_key, now(),
        )
    except Exception:
        await env(request).UPLOADS.delete(object_key)
        raise
    return await _get(request, file_id)


@router.get("/{file_id}/content")
async def file_content(file_id: str, request: Request) -> Response:
    record = await _get(request, file_id)
    item = await env(request).UPLOADS.get(record["object_key"])
    if item is None:
        raise HTTPException(404, "file content not found")
    raw = await item.arrayBuffer()
    content = raw.to_bytes() if hasattr(raw, "to_bytes") else bytes(raw)
    disposition = "inline" if record["mime_type"].startswith("image/") else "attachment"
    return Response(
        content=content,
        media_type=record["mime_type"],
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(record['original_name'])}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, request: Request) -> Response:
    record = await _get(request, file_id)
    await env(request).UPLOADS.delete(record["object_key"])
    await db(request).run("DELETE FROM uploaded_files WHERE id = ?", file_id)
    return Response(status_code=204)
