from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.app.schemas.chat import ChatRequest, ChatResponse
from src.app.skill.assets import DOCUMENTS
from src.app.skill.composer import PromptComposer
from src.app.skill.router import SkillRouter
from src.app.skill.types import SkillDocument
from src.common import db, env, new_id, now, require
from src.routes.memories import memory_context
from src.routes.settings import values as setting_values


router = APIRouter(prefix="/api/chat", tags=["chat"])
MAX_IMAGE_PAYLOAD = 12 * 1024 * 1024


def _document(path: str) -> SkillDocument:
    content = DOCUMENTS[path]
    title = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), path)
    return SkillDocument(path=path, title=title, content=content)


async def _model_complete(request: Request, messages: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    injected = request.scope.get("model_complete")
    if injected is not None:
        return await injected(messages)
    settings = await setting_values(request)
    api_key = settings.pop("api_key")
    if not api_key:
        raise HTTPException(503, "GOUTOU_API_KEY Worker Secret is not configured")
    base_url = settings["base_url"].rstrip("/")
    if not base_url.startswith("https://"):
        raise HTTPException(503, "model base_url must use HTTPS")
    from workers import fetch

    try:
        response = await fetch(
            base_url + "/chat/completions",
            method="POST",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            body=json.dumps({
                "model": settings["model"], "messages": messages,
                "temperature": settings["temperature"], "max_tokens": settings["max_tokens"],
                "stream": False,
            }, ensure_ascii=False),
        )
    except Exception as exc:
        raise HTTPException(503, "model service is unavailable") from exc
    if not response.ok:
        raise HTTPException(503, f"model service returned HTTP {response.status}")
    try:
        payload = json.loads(await response.text())
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("model content must be text")
        raw_usage = payload.get("usage") or {}
        usage = {key: int(value) for key, value in raw_usage.items() if isinstance(value, (int, float))}
        return content, usage
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(503, "model service returned an invalid response") from exc


async def _prepare(request: Request, payload: ChatRequest) -> tuple[list[dict[str, Any]], Any, str, str]:
    database = db(request)
    conversation = require(
        await database.one("SELECT * FROM conversations WHERE id = ?", payload.conversation_id),
        "conversation",
    )
    if payload.person_id is not None:
        require(await database.one("SELECT id FROM people WHERE id = ?", payload.person_id), "person")
        await database.run(
            "UPDATE conversations SET person_id = ?, updated_at = ? WHERE id = ?",
            payload.person_id, now(), payload.conversation_id,
        )
        conversation["person_id"] = payload.person_id
    person = None
    relationship = None
    if conversation["person_id"]:
        person = await database.one("SELECT * FROM people WHERE id = ?", conversation["person_id"])
        relationship = await database.one("SELECT * FROM relationships WHERE person_id = ?", conversation["person_id"])

    previous = await database.all(
        "SELECT rowid, id, role, content, metadata FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
        payload.conversation_id,
    )
    current_text = payload.message
    file_ids = list(payload.file_ids)
    if payload.regenerate:
        last_user = next((item for item in reversed(previous) if item["role"] == "user"), None)
        if last_user is None:
            raise HTTPException(404, "user message not found")
        current_text = last_user["content"]
        if not file_ids and last_user["metadata"]:
            file_ids = list((json.loads(last_user["metadata"]) or {}).get("file_ids") or [])
        await database.run(
            "DELETE FROM messages WHERE conversation_id = ? AND rowid > ?",
            payload.conversation_id, last_user["rowid"],
        )
        previous = [item for item in previous if item["rowid"] < last_user["rowid"]]
    else:
        metadata = json.dumps({"file_ids": file_ids}) if file_ids else None
        await database.run(
            "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, 'user', ?, ?, ?)",
            new_id(), payload.conversation_id, current_text, metadata, now(),
        )
        title = current_text.strip().replace("\n", " ")[:32] if conversation["title"] == "新对话" else conversation["title"]
        await database.run("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?", title, now(), payload.conversation_id)

    files = []
    for file_id in file_ids:
        files.append(require(await database.one("SELECT * FROM uploaded_files WHERE id = ?", file_id), "file"))
    route = SkillRouter().route(
        current_text,
        relationship_status=relationship["status"] if relationship else None,
        file_types=[item["mime_type"] for item in files],
    )
    context = await memory_context(person["id"], request, max_chars=4000) if person else None
    composed = PromptComposer().compose(
        core_skill=_document("SKILL.md"), route=route, user_message=current_text,
        references=[_document(path) for path in route.references],
        person={key: person[key] for key in ("id", "display_name", "notes")} if person else None,
        relationship={key: relationship[key] for key in ("status", "notes")} if relationship else None,
        memories=context,
        history=[{"role": item["role"], "content": item["content"]} for item in previous if item["role"] in {"user", "assistant"}],
    )
    images = [item for item in files if item["mime_type"].startswith("image/")]
    if sum(item["size"] for item in images) > MAX_IMAGE_PAYLOAD:
        raise HTTPException(400, "images exceed the 12 MB cloud model payload limit")
    if images:
        attachments = []
        for record in images:
            item = await env(request).UPLOADS.get(record["object_key"])
            if item is None:
                raise HTTPException(404, "file content not found")
            raw = await item.arrayBuffer()
            content = raw.to_bytes() if hasattr(raw, "to_bytes") else bytes(raw)
            attachments.append({"type": "image_url", "image_url": {
                "url": f"data:{record['mime_type']};base64,{base64.b64encode(content).decode('ascii')}"
            }})
        composed[-1]["content"] = [{"type": "text", "text": current_text}, *attachments]
    return composed, route, payload.conversation_id, current_text


async def _save_assistant(request: Request, conversation_id: str, content: str, route: Any) -> str:
    message_id = new_id()
    await db(request).run(
        "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, 'assistant', ?, ?, ?)",
        message_id, conversation_id, content,
        json.dumps({"intent": route.intent, "risk": route.risk, "references": list(route.references), "provider": "openai-compatible"}),
        now(),
    )
    await db(request).run("UPDATE conversations SET updated_at = ? WHERE id = ?", now(), conversation_id)
    return message_id


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    messages, route, conversation_id, _ = await _prepare(request, payload)
    content, usage = await _model_complete(request, messages)
    message_id = await _save_assistant(request, conversation_id, content, route)
    return ChatResponse(
        conversation_id=conversation_id, message_id=message_id, content=content,
        intent=route.intent, risk=route.risk, references=list(route.references), usage=usage,
    )


@router.post("/stream")
async def stream_chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    async def events():
        try:
            messages, route, conversation_id, _ = await _prepare(request, payload)
            yield "event: meta\ndata: " + json.dumps({
                "conversation_id": conversation_id, "intent": route.intent,
                "risk": route.risk, "references": list(route.references),
            }, ensure_ascii=False) + "\n\n"
            content, _ = await _model_complete(request, messages)
            yield "event: delta\ndata: " + json.dumps({"content": content}, ensure_ascii=False) + "\n\n"
            message_id = await _save_assistant(request, conversation_id, content, route)
            yield "event: done\ndata: " + json.dumps({"message_id": message_id}) + "\n\n"
        except HTTPException as exc:
            yield "event: error\ndata: " + json.dumps({"detail": exc.detail}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
