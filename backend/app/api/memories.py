from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.memory import MemoryContext, MemoryCreate, MemoryRead, MemoryScope, MemoryUpdate
from app.services.memory_service import MemoryNotFoundError, MemoryService, PersonNotFoundError


router = APIRouter(prefix="/api/memories", tags=["memories"])
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[MemoryRead])
def list_memories(
    db: Database,
    person_id: str | None = None,
    scope: MemoryScope | None = None,
) -> list[MemoryRead]:
    return [MemoryRead.model_validate(item) for item in MemoryService(db).list(person_id=person_id, scope=scope)]


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate, db: Database) -> MemoryRead:
    try:
        return MemoryRead.model_validate(MemoryService(db).create(payload))
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail="person not found") from exc


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: str, payload: MemoryUpdate, db: Database) -> MemoryRead:
    try:
        return MemoryRead.model_validate(MemoryService(db).update(memory_id, payload))
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory not found") from exc


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, db: Database) -> Response:
    try:
        MemoryService(db).delete(memory_id)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/context/{person_id}", response_model=MemoryContext)
def memory_context(
    person_id: str,
    db: Database,
    max_chars: int = Query(4000, ge=500, le=8000),
) -> MemoryContext:
    try:
        return MemoryService(db).get_context(person_id, max_chars=max_chars)
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail="person not found") from exc


@router.delete("/person/{person_id}")
def clear_person_memories(person_id: str, db: Database) -> dict[str, int]:
    return {"deleted": MemoryService(db).clear_person(person_id)}


@router.delete("")
def clear_all_memories(db: Database, confirm: bool = Query(False)) -> dict[str, int]:
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")
    return {"deleted": MemoryService(db).clear_all()}

