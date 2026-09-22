from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.file import FileRead
from app.services.file_service import FileNotFoundError, FileService, FileValidationError


router = APIRouter(prefix="/api/files", tags=["files"])
Database = Annotated[Session, Depends(get_db)]
Configuration = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=list[FileRead])
def list_files(db: Database, settings: Configuration) -> list[FileRead]:
    return [FileRead.model_validate(item) for item in FileService(db, settings.upload_dir).list()]


@router.post("", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    db: Database,
    settings: Configuration,
    file: UploadFile = File(...),
) -> FileRead:
    try:
        return FileRead.model_validate(await FileService(db, settings.upload_dir).save(file))
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{file_id}/content")
def file_content(file_id: str, db: Database, settings: Configuration) -> FileResponse:
    try:
        record = FileService(db, settings.upload_dir).get(file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc
    return FileResponse(Path(record.path), media_type=record.mime_type, filename=record.original_name)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: str, db: Database, settings: Configuration) -> Response:
    try:
        FileService(db, settings.upload_dir).delete(file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

