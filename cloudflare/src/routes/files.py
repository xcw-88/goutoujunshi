"""Compatibility routes: cloud attachments are request-scoped, never stored."""

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api/files", tags=["files"])


def _gone() -> None:
    raise HTTPException(410, "cloud files are temporary; attach them to a chat or import request")


@router.get("")
async def list_files() -> None:
    _gone()


@router.post("")
async def upload_file() -> None:
    _gone()


@router.get("/{file_id}/content")
async def file_content(file_id: str) -> None:
    _gone()


@router.delete("/{file_id}")
async def delete_file(file_id: str) -> None:
    _gone()
