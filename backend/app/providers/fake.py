from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.providers.base import ModelResponse


class FakeModelProvider:
    name = "fake"

    def __init__(self, content: str = "这是一个用于测试的回复。") -> None:
        self.content = content
        self.calls: list[list[dict[str, Any]]] = []

    async def chat(self, messages: list[dict[str, Any]], **_: Any) -> ModelResponse:
        self.calls.append(messages)
        return ModelResponse(
            content=self.content,
            usage={"prompt_tokens": 100, "completion_tokens": 20},
        )

    async def stream_chat(
        self, messages: list[dict[str, Any]], **_: Any
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        for index in range(0, len(self.content), 4):
            yield self.content[index : index + 4]

