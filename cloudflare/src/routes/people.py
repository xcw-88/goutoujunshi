from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.schemas.person import PersonCreate, PersonRead, PersonUpdate, RelationshipRead, RelationshipWrite
from common import db, new_id, now, require


router = APIRouter(prefix="/api/people", tags=["people"])
PERSON_SELECT = """
SELECT p.*, r.id AS relationship_id, r.status AS relationship_status,
       r.notes AS relationship_notes, r.created_at AS relationship_created_at,
       r.updated_at AS relationship_updated_at
FROM people p LEFT JOIN relationships r ON r.person_id = p.id
"""


def _person(row: dict) -> dict:
    result = {key: row[key] for key in ("id", "display_name", "notes", "created_at", "updated_at")}
    result["relationship_profile"] = (
        {
            "id": row["relationship_id"],
            "person_id": row["id"],
            "status": row["relationship_status"],
            "notes": row["relationship_notes"],
            "created_at": row["relationship_created_at"],
            "updated_at": row["relationship_updated_at"],
        }
        if row["relationship_id"] else None
    )
    return result


async def _get(request: Request, person_id: str) -> dict:
    row = require(await db(request).one(PERSON_SELECT + " WHERE p.id = ?", person_id), "person")
    return _person(row)


@router.get("", response_model=list[PersonRead])
async def list_people(request: Request) -> list[dict]:
    return [_person(row) for row in await db(request).all(PERSON_SELECT + " ORDER BY p.updated_at DESC")]


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(payload: PersonCreate, request: Request) -> dict:
    person_id, timestamp = new_id(), now()
    await db(request).run(
        "INSERT INTO people (id, display_name, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        person_id, payload.display_name, payload.notes, timestamp, timestamp,
    )
    return await _get(request, person_id)


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(person_id: str, request: Request) -> dict:
    return await _get(request, person_id)


@router.patch("/{person_id}", response_model=PersonRead)
async def update_person(person_id: str, payload: PersonUpdate, request: Request) -> dict:
    await _get(request, person_id)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(422, "person fields cannot be null")
    for key in ("display_name", "notes"):
        if key in changes:
            await db(request).run(f"UPDATE people SET {key} = ?, updated_at = ? WHERE id = ?", changes[key], now(), person_id)
    return await _get(request, person_id)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(person_id: str, request: Request) -> Response:
    await _get(request, person_id)
    await db(request).run("DELETE FROM people WHERE id = ?", person_id)
    return Response(status_code=204)


@router.get("/{person_id}/relationship", response_model=RelationshipRead)
async def get_relationship(person_id: str, request: Request) -> dict:
    person = await _get(request, person_id)
    return require(person["relationship_profile"], "relationship")


@router.put("/{person_id}/relationship", response_model=RelationshipRead)
async def upsert_relationship(person_id: str, payload: RelationshipWrite, request: Request) -> dict:
    person = await _get(request, person_id)
    timestamp = now()
    existing = person["relationship_profile"]
    if existing:
        await db(request).run(
            "UPDATE relationships SET status = ?, notes = ?, updated_at = ? WHERE person_id = ?",
            payload.status, payload.notes, timestamp, person_id,
        )
    else:
        await db(request).run(
            "INSERT INTO relationships (id, person_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            new_id(), person_id, payload.status, payload.notes, timestamp, timestamp,
        )
    return (await _get(request, person_id))["relationship_profile"]
