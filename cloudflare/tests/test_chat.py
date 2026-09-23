from tests.conftest import client_with_env
import json
import sys
from types import SimpleNamespace

from tests.fake_bindings import D1Binding


def test_chat_uses_canonical_skill_and_saves_answer() -> None:
    seen = []

    async def model(messages):
        seen.append(messages)
        return "请先确保自身安全。", {"total_tokens": 42}

    with client_with_env(DB=D1Binding(), model_complete=model) as client:
        person_id = client.post("/api/people", json={"display_name": "A"}).json()["id"]
        conversation_id = client.post("/api/conversations", json={"person_id": person_id}).json()["id"]
        answer = client.post("/api/chat", json={
            "conversation_id": conversation_id, "message": "他威胁我，怎么办？", "file_ids": [],
        })
        assert answer.status_code == 200
        assert answer.json()["risk"] == "high"
        assert answer.json()["usage"] == {"total_tokens": 42}
        assert "CORE SKILL RULES" in seen[0][0]["content"]
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
        stream = client.post("/api/chat/stream", json={
            "conversation_id": conversation_id, "message": "怎么回复？", "file_ids": [],
        })
        assert "event: meta" in stream.text
        assert "event: delta" in stream.text
        assert "event: done" in stream.text


def test_chat_uses_temporary_text_without_saving_it() -> None:
    seen = []

    async def model(messages):
        seen.append(messages)
        return "已看过", {}

    with client_with_env(DB=D1Binding(), model_complete=model) as client:
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        payload = {"conversation_id": conversation_id, "message": "请分析附件", "file_ids": []}
        response = client.post("/api/chat", data={"payload": json.dumps(payload)}, files={
            "files": ("private.txt", b"PRIVATE_FILE_BODY", "text/plain"),
        })
        assert response.status_code == 200
        assert "PRIVATE_FILE_BODY" in seen[0][-1]["content"]
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        assert all("PRIVATE_FILE_BODY" not in item["content"] for item in detail["messages"])
        assert detail["messages"][0]["metadata_json"]["attachment_types"] == ["text/plain"]
        regen = client.post("/api/chat", json={**payload, "regenerate": True})
        assert regen.status_code == 409
        assert len(client.get(f"/api/conversations/{conversation_id}").json()["messages"]) == 2


def test_invalid_temporary_attachment_does_not_create_message() -> None:
    async def model(messages):
        return "unused", {}

    with client_with_env(DB=D1Binding(), model_complete=model) as client:
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        payload = {"conversation_id": conversation_id, "message": "看文件"}
        invalid = client.post("/api/chat", data={"payload": json.dumps(payload)}, files={
            "files": ("bad.txt", b"\xff", "text/plain"),
        })
        assert invalid.status_code == 400
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        assert detail["messages"] == []


def test_chat_switches_provider_secret_with_base_url(monkeypatch) -> None:
    calls = []

    class Response:
        ok = True
        status = 200

        async def text(self):
            return json.dumps({"choices": [{"message": {"content": "已回复"}}], "usage": {"total_tokens": 3}})

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setitem(sys.modules, "workers", SimpleNamespace(fetch=fake_fetch))
    with client_with_env(
        DB=D1Binding(), GOUTOU_API_BASE="https://api.openai.com/v1",
        GOUTOU_MODEL="gpt-4.1-mini", GOUTOU_API_KEY="openai-secret",
        GOUTOU_GEMINI_API_KEY="gemini-secret",
    ) as client:
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        first = client.post("/api/chat", json={"conversation_id": conversation_id, "message": "你好"})
        assert first.status_code == 200
        assert calls[-1][0] == "https://api.openai.com/v1/chat/completions"
        assert calls[-1][1]["headers"]["Authorization"] == "Bearer openai-secret"
        client.patch("/api/settings", json={
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "model": "gemini-3.8-flash",
        })
        second = client.post("/api/chat", json={"conversation_id": conversation_id, "message": "再说一次"})
        assert second.status_code == 200
        assert calls[-1][0] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        assert calls[-1][1]["headers"]["Authorization"] == "Bearer gemini-secret"
        assert json.loads(calls[-1][1]["body"])["model"] == "gemini-3.8-flash"
