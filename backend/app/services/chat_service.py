from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Message, Person
from app.providers.base import ModelProvider, ModelResponse
from app.schemas.chat import ChatRequest
from app.services.memory_service import MemoryService
from app.skill.composer import PromptComposer
from app.skill.loader import SkillLoader
from app.skill.router import SkillRouter
from app.skill.types import RouteDecision


class ChatNotFoundError(LookupError):
    pass


class ChatService:
    def __init__(
        self,
        session: Session,
        provider: ModelProvider,
        *,
        loader: SkillLoader | None = None,
        router: SkillRouter | None = None,
        composer: PromptComposer | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.loader = loader or SkillLoader()
        self.router = router or SkillRouter()
        self.composer = composer or PromptComposer()

    async def chat(self, request: ChatRequest) -> tuple[Message, ModelResponse, RouteDecision]:
        conversation, messages, route = self._prepare(request)
        response = await self.provider.chat(messages)
        assistant = self._save_assistant(conversation, response.content, route)
        return assistant, response, route

    async def stream(self, request: ChatRequest) -> AsyncIterator[tuple[str, Any]]:
        conversation, messages, route = self._prepare(request)
        yield "meta", {
            "conversation_id": conversation.id,
            "intent": route.intent,
            "risk": route.risk,
            "references": list(route.references),
        }
        parts: list[str] = []
        async for chunk in self.provider.stream_chat(messages):
            parts.append(chunk)
            yield "delta", {"content": chunk}
        assistant = self._save_assistant(conversation, "".join(parts), route)
        yield "done", {"message_id": assistant.id}

    def _prepare(
        self, request: ChatRequest
    ) -> tuple[Conversation, list[dict[str, Any]], RouteDecision]:
        conversation = self.session.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.person).selectinload(Person.relationship_profile))
            .where(Conversation.id == request.conversation_id)
        )
        if conversation is None:
            raise ChatNotFoundError("conversation")
        if request.person_id is not None:
            person = self.session.get(Person, request.person_id)
            if person is None:
                raise ChatNotFoundError("person")
            conversation.person_id = person.id
            conversation.person = person
        person = conversation.person
        relationship = person.relationship_profile if person else None
        user_message = Message(role="user", content=request.message, conversation=conversation)
        self.session.add(user_message)
        if conversation.title == "新对话":
            conversation.title = request.message.strip().replace("\n", " ")[:32]
        self.session.commit()

        route = self.router.route(
            request.message,
            relationship_status=relationship.status if relationship else None,
        )
        documents = self.loader.load_references(route.references)
        memory_context = MemoryService(self.session).get_context(person.id) if person else None
        history = [
            {"role": item.role, "content": item.content}
            for item in conversation.messages
            if item.id != user_message.id and item.role in {"user", "assistant"}
        ]
        composed = self.composer.compose(
            core_skill=self.loader.load_skill(),
            route=route,
            user_message=request.message,
            references=documents,
            person={"id": person.id, "display_name": person.display_name, "notes": person.notes}
            if person
            else None,
            relationship={"status": relationship.status, "notes": relationship.notes}
            if relationship
            else None,
            memories=memory_context,
            history=history,
        )
        return conversation, composed, route

    def _save_assistant(
        self, conversation: Conversation, content: str, route: RouteDecision
    ) -> Message:
        message = Message(
            role="assistant",
            content=content,
            metadata_json={
                "intent": route.intent,
                "risk": route.risk,
                "references": list(route.references),
                "provider": self.provider.name,
            },
            conversation=conversation,
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

