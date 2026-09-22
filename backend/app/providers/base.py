from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class ModelResponse:
    content: str
    usage: dict[str, int] = field(default_factory=dict)


class ProviderError(RuntimeError):
    pass


class ModelProvider(Protocol):
    name: str

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> ModelResponse: ...

    def stream_chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[str]: ...

