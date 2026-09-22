from fastapi.testclient import TestClient

from app.main import app
from app.providers.dependencies import get_model_provider
from app.providers.fake import FakeModelProvider


def test_chat_uses_fake_provider_and_persists_messages(client: TestClient) -> None:
    fake = FakeModelProvider("先稳住，再看持续投入。")
    app.dependency_overrides[get_model_provider] = lambda: fake
    conversation = client.post("/api/conversations", json={}).json()

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation["id"],
            "message": "她最近忽冷忽热，我该怎么看？",
        },
    )

    assert response.status_code == 200
    assert response.json()["content"] == "先稳住，再看持续投入。"
    assert response.json()["intent"] == "general_relationship_analysis"
    detail = client.get(f"/api/conversations/{conversation['id']}").json()
    assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
    assert detail["title"].startswith("她最近忽冷忽热")
    assert "CORE SKILL RULES" in fake.calls[0][0]["content"]


def test_stream_chat_emits_sse_and_persists_on_completion(client: TestClient) -> None:
    fake = FakeModelProvider("流式回复")
    app.dependency_overrides[get_model_provider] = lambda: fake
    conversation = client.post("/api/conversations", json={}).json()

    response = client.post(
        "/api/chat/stream",
        json={"conversation_id": conversation["id"], "message": "怎么回复她？"},
    )

    assert response.status_code == 200
    assert "event: meta" in response.text
    assert "event: delta" in response.text
    assert "event: done" in response.text
    detail = client.get(f"/api/conversations/{conversation['id']}").json()
    assert detail["messages"][-1]["content"] == "流式回复"

    fake.content = "重新生成的回复"
    regenerated = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conversation["id"],
            "message": "客户端显示的原问题",
            "regenerate": True,
        },
    )
    assert "event: done" in regenerated.text
    detail = client.get(f"/api/conversations/{conversation['id']}").json()
    assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][-1]["content"] == "重新生成的回复"
