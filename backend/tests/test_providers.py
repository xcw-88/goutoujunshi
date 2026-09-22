import json

import httpx
import pytest

from app.providers.fake import FakeModelProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_fake_provider_never_calls_network() -> None:
    provider = FakeModelProvider("fake-response")
    messages = [{"role": "user", "content": "hello"}]

    response = await provider.chat(messages)
    chunks = [chunk async for chunk in provider.stream_chat(messages)]

    assert response.content == "fake-response"
    assert "".join(chunks) == "fake-response"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_openai_compatible_payload_and_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1/",
            api_key="test-key",
            model="test-model",
            client=client,
        )
        response = await provider.chat([{"role": "user", "content": "hello"}])

    assert response.content == "ok"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["payload"] == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.7,
        "max_tokens": 1200,
        "stream": False,
    }


@pytest.mark.asyncio
async def test_openai_compatible_stream() -> None:
    body = (
        'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="test-model",
            client=client,
        )
        result = "".join([part async for part in provider.stream_chat([])])

    assert result == "你好"
