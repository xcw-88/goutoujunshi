from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationRead, ConversationUpdate
from common import db, new_id, now, require


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


async def _person_exists(request: Request, person_id: str | None) -> None:
    if person_id and not await db(request).one("SELECT id FROM people WHERE id = ?", person_id):
        raise HTTPException(404, "person not found")


async def _get(request: Request, conversation_id: str) -> dict:
    return require(await db(request).one("SELECT * FROM conversations WHERE id = ?", conversation_id), "conversation")


@router.get("", response_model=list[ConversationRead])
async def list_conversations(request: Request) -> list[dict]:
    return await db(request).all("SELECT * FROM conversations ORDER BY updated_at DESC")


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationCreate, request: Request) -> dict:
    await _person_exists(request, payload.person_id)
    conversation_id, timestamp = new_id(), now()
    await db(request).run(
        "INSERT INTO conversations (id, title, person_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        conversation_id, payload.title, payload.person_id, timestamp, timestamp,
    )
    return await _get(request, conversation_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, request: Request) -> dict:
    conversation = await _get(request, conversation_id)
    messages = await db(request).all(
        "SELECT id, role, content, metadata, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
        conversation_id,
    )
    conversation["messages"] = [
        {**message, "metadata_json": json.loads(message.pop("metadata")) if message["metadata"] else None}
        for message in messages
    ]
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(conversation_id: str, payload: ConversationUpdate, request: Request) -> dict:
    await _get(request, conversation_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.pop("unbind_person", False):
        changes["person_id"] = None
    if "person_id" in changes:
        await _person_exists(request, changes["person_id"])
    for key in ("title", "person_id"):
        if key in changes:
            if key == "title" and changes[key] is None:
                raise HTTPException(422, "title cannot be null")
            await db(request).run(
                f"UPDATE conversations SET {key} = ?, updated_at = ? WHERE id = ?",
                changes[key], now(), conversation_id,
            )
    return await _get(request, conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, request: Request) -> Response:
    await _get(request, conversation_id)
    await db(request).run("DELETE FROM conversations WHERE id = ?", conversation_id)
    return Response(status_code=204)
