from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding, R2Binding


def test_chat_uses_canonical_skill_and_saves_answer() -> None:
    seen = []

    async def model(messages):
        seen.append(messages)
        return "请先确保自身安全。", {"total_tokens": 42}

    with client_with_env(DB=D1Binding(), UPLOADS=R2Binding(), model_complete=model) as client:
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
