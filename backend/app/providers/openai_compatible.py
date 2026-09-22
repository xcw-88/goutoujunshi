from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import ModelResponse, ProviderError


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1200,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = client

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> ModelResponse:
        payload = self._payload(messages, stream=False, **kwargs)
        async with self._client_context() as client:
            try:
                response = await client.post(self._endpoint, headers=self._headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage") or {}
                return ModelResponse(content=content or "", usage=usage)
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                raise ProviderError(f"model request failed: {exc.__class__.__name__}") from exc

    async def stream_chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, stream=True, **kwargs)
        async with self._client_context() as client:
            try:
                async with client.stream(
                    "POST", self._endpoint, headers=self._headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line.removeprefix("data:").strip()
                        if raw == "[DONE]":
                            break
                        if not raw:
                            continue
                        data = json.loads(raw)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content:
                            yield content
            except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise ProviderError(f"model stream failed: {exc.__class__.__name__}") from exc

    @property
    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError("GOUTOU_API_KEY is not configured")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(
        self, messages: list[dict[str, Any]], *, stream: bool, **kwargs: Any
    ) -> dict[str, Any]:
        return {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": stream,
        }

    def _client_context(self) -> _ClientContext:
        return _ClientContext(self._client)


class _ClientContext:
    def __init__(self, client: httpx.AsyncClient | None) -> None:
        self.client = client
        self.owned = client is None

    async def __aenter__(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=60)
        return self.client

    async def __aexit__(self, *_: object) -> None:
        if self.owned and self.client is not None:
            await self.client.aclose()

