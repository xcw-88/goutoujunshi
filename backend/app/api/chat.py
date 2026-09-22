from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.providers.base import ModelProvider, ProviderError
from app.providers.dependencies import get_model_provider
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatNotFoundError, ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])
Database = Annotated[Session, Depends(get_db)]
Provider = Annotated[ModelProvider, Depends(get_model_provider)]


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Database, provider: Provider) -> ChatResponse:
    try:
        message, response, route = await ChatService(db, provider).chat(payload)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"{exc.args[0]} not found") from exc
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(
        conversation_id=payload.conversation_id,
        message_id=message.id,
        content=response.content,
        intent=route.intent,
        risk=route.risk,
        references=list(route.references),
        usage=response.usage,
    )


@router.post("/stream")
async def stream_chat(payload: ChatRequest, db: Database, provider: Provider) -> StreamingResponse:
    async def events():
        try:
            async for event, data in ChatService(db, provider).stream(payload):
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except ChatNotFoundError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': f'{exc.args[0]} not found'})}\n\n"
        except ProviderError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

