from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.schemas.chat import ChatRequest, ChatResponse
from app.skill.assets import DOCUMENTS
from app.skill.composer import PromptComposer
from app.skill.router import SkillRouter
from app.skill.types import SkillDocument
from common import db, new_id, now, require
from routes.memories import memory_context
from routes.settings import api_key_secret, values as setting_values
from transient_files import MAX_TEXT_CHARS, TransientFile, read_uploads


router = APIRouter(prefix="/api/chat", tags=["chat"])

async def _input(request: Request) -> tuple[ChatRequest, list[TransientFile]]:
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            payload = ChatRequest.model_validate_json(str(form.get("payload", "")))
            uploads = form.getlist("files")
            if any(not isinstance(item, UploadFile) for item in uploads):
                raise HTTPException(400, "invalid attachments")
            files = await read_uploads(uploads)
        elif content_type.startswith("application/json"):
            payload = ChatRequest.model_validate(await request.json())
            files = []
        else:
            raise HTTPException(415, "expected JSON or multipart form")
    except (ValidationError, ValueError) as exc:
        raise HTTPException(422, "invalid chat request") from exc
    if payload.file_ids:
        raise HTTPException(410, "stored files are unavailable in cloud mode; select files for this request")
    return payload, files


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
        raise HTTPException(503, f"{api_key_secret(settings['base_url'])} Worker Secret is not configured")
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


def _attachment_content(current_text: str, files: list[TransientFile]) -> str | list[dict[str, Any]]:
    text_parts = [current_text]
    attachments = []
    for item in files:
        if item.mime_type.startswith("image/"):
            attachments.append({"type": "image_url", "image_url": {
                "url": f"data:{item.mime_type};base64,{base64.b64encode(item.content).decode('ascii')}"
            }})
        else:
            try:
                decoded = item.content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(400, "text attachments must use UTF-8") from exc
            text_parts.append(f"\n\n[临时附件：{item.name}]\n{decoded}")
    model_text = "".join(text_parts)
    if len(model_text) > MAX_TEXT_CHARS:
        raise HTTPException(413, "text attachments exceed the cloud context limit")
    return ([{"type": "text", "text": model_text}, *attachments] if attachments else model_text)


async def _prepare(request: Request, payload: ChatRequest, files: list[TransientFile]) -> tuple[list[dict[str, Any]], Any, str, str]:
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
    if payload.regenerate:
        last_user = next((item for item in reversed(previous) if item["role"] == "user"), None)
        if last_user is None:
            raise HTTPException(404, "user message not found")
        current_text = last_user["content"]
        if last_user["metadata"]:
            metadata = json.loads(last_user["metadata"]) or {}
            if (metadata.get("attachment_types") or metadata.get("file_ids")) and not files:
                raise HTTPException(409, "reselect the original attachment before regenerating")
        model_content = _attachment_content(current_text, files)
        await database.run(
            "DELETE FROM messages WHERE conversation_id = ? AND rowid > ?",
            payload.conversation_id, last_user["rowid"],
        )
        previous = [item for item in previous if item["rowid"] < last_user["rowid"]]
    else:
        model_content = _attachment_content(current_text, files)
        metadata = json.dumps({"attachment_types": [item.mime_type for item in files]}) if files else None
        await database.run(
            "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, 'user', ?, ?, ?)",
            new_id(), payload.conversation_id, current_text, metadata, now(),
        )
        title = current_text.strip().replace("\n", " ")[:32] if conversation["title"] == "新对话" else conversation["title"]
        await database.run("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?", title, now(), payload.conversation_id)

    route = SkillRouter().route(
        current_text,
        relationship_status=relationship["status"] if relationship else None,
        file_types=[item.mime_type for item in files],
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
    composed[-1]["content"] = model_content
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
async def chat(request: Request) -> ChatResponse:
    payload, files = await _input(request)
    messages, route, conversation_id, _ = await _prepare(request, payload, files)
    content, usage = await _model_complete(request, messages)
    message_id = await _save_assistant(request, conversation_id, content, route)
    return ChatResponse(
        conversation_id=conversation_id, message_id=message_id, content=content,
        intent=route.intent, risk=route.risk, references=list(route.references), usage=usage,
    )


@router.post("/stream")
async def stream_chat(request: Request) -> StreamingResponse:
    payload, files = await _input(request)
    async def events():
        try:
            messages, route, conversation_id, _ = await _prepare(request, payload, files)
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
