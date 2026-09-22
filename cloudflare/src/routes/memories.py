from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.schemas.memory import MemoryContext, MemoryCreate, MemoryRead, MemoryScope, MemoryUpdate
from common import db, new_id, now, require


router = APIRouter(prefix="/api/memories", tags=["memories"])


async def _person_exists(request: Request, person_id: str | None) -> None:
    if person_id and not await db(request).one("SELECT id FROM people WHERE id = ?", person_id):
        raise HTTPException(404, "person not found")


async def _get(request: Request, memory_id: str) -> dict:
    return require(await db(request).one("SELECT * FROM memories WHERE id = ?", memory_id), "memory")


@router.get("", response_model=list[MemoryRead])
async def list_memories(request: Request, person_id: str | None = None, scope: MemoryScope | None = None) -> list[dict]:
    filters, values = [], []
    if person_id is not None:
        filters.append("person_id = ?")
        values.append(person_id)
    if scope is not None:
        filters.append("scope = ?")
        values.append(scope)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    return await db(request).all("SELECT * FROM memories" + where + " ORDER BY updated_at DESC", *values)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate, request: Request) -> dict:
    await _person_exists(request, payload.person_id)
    memory_id, timestamp = new_id(), now()
    await db(request).run(
        """INSERT INTO memories
        (id, person_id, scope, key, value, confidence, source, occurred_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        memory_id, payload.person_id, payload.scope, payload.key, payload.value,
        payload.confidence, payload.source,
        payload.occurred_at.isoformat() if payload.occurred_at else None,
        timestamp, timestamp,
    )
    return await _get(request, memory_id)


@router.patch("/{memory_id}", response_model=MemoryRead)
async def update_memory(memory_id: str, payload: MemoryUpdate, request: Request) -> dict:
    current = await _get(request, memory_id)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    candidate = MemoryCreate.model_validate({
        key: changes.get(key, current[key])
        for key in ("person_id", "scope", "key", "value", "confidence", "source", "occurred_at")
    })
    await db(request).run(
        "UPDATE memories SET value = ?, confidence = ?, source = ?, occurred_at = ?, updated_at = ? WHERE id = ?",
        candidate.value, candidate.confidence, candidate.source,
        candidate.occurred_at.isoformat() if candidate.occurred_at else None,
        now(), memory_id,
    )
    return await _get(request, memory_id)


@router.delete("/person/{person_id}")
async def clear_person_memories(person_id: str, request: Request) -> dict[str, int]:
    return {"deleted": await db(request).run("DELETE FROM memories WHERE person_id = ?", person_id)}


@router.delete("")
async def clear_all_memories(request: Request, confirm: bool = Query(False)) -> dict[str, int]:
    if not confirm:
        raise HTTPException(400, "confirm=true is required")
    return {"deleted": await db(request).run("DELETE FROM memories")}


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str, request: Request) -> Response:
    await _get(request, memory_id)
    await db(request).run("DELETE FROM memories WHERE id = ?", memory_id)
    return Response(status_code=204)


@router.get("/context/{person_id}", response_model=MemoryContext)
async def memory_context(person_id: str, request: Request, max_chars: int = Query(4000, ge=500, le=8000)) -> MemoryContext:
    await _person_exists(request, person_id)
    database = db(request)
    stable = await database.all(
        "SELECT * FROM memories WHERE scope IN ('user', 'object', 'relationship') AND (person_id = ? OR person_id IS NULL) ORDER BY updated_at DESC",
        person_id,
    )
    events = await database.all(
        "SELECT * FROM memories WHERE person_id = ? AND scope = 'event' ORDER BY occurred_at DESC, updated_at DESC LIMIT 8",
        person_id,
    )
    hypotheses = await database.all(
        "SELECT * FROM memories WHERE person_id = ? AND scope = 'hypothesis' ORDER BY updated_at DESC LIMIT 5",
        person_id,
    )
    groups = {
        "confirmed_facts": [MemoryRead.model_validate(row) for row in stable],
        "events": [MemoryRead.model_validate(row) for row in events],
        "hypotheses": [MemoryRead.model_validate(row) for row in hypotheses],
    }
    while len(json.dumps({key: [item.model_dump(mode="json") for item in values] for key, values in groups.items()}, ensure_ascii=False)) > max_chars:
        for key in ("hypotheses", "events", "confirmed_facts"):
            if groups[key]:
                groups[key].pop()
                break
        else:
            break
    return MemoryContext(**groups)
