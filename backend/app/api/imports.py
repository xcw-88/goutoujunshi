from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.imports import ImportConfirmRequest, ImportPreview, ImportPreviewRequest, ImportResult
from app.services.import_service import ImportService, ImportValidationError


router = APIRouter(prefix="/api/imports", tags=["imports"])
Database = Annotated[Session, Depends(get_db)]


@router.post("/preview", response_model=ImportPreview)
def preview_import(payload: ImportPreviewRequest, db: Database) -> ImportPreview:
    try:
        return ImportService(db).preview(payload.file_id)
    except ImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/confirm", response_model=ImportResult)
def confirm_import(payload: ImportConfirmRequest, db: Database) -> ImportResult:
    try:
        conversation, count = ImportService(db).confirm(payload)
    except ImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportResult(conversation_id=conversation.id, imported_messages=count)

