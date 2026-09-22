from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding, R2Binding


def test_import_preview_and_confirm_speaker_mapping() -> None:
    with client_with_env(DB=D1Binding(), UPLOADS=R2Binding()) as client:
        file_id = client.post("/api/files", files={
            "file": ("chat.txt", "Alice: 你好\nBob: 你好啊".encode(), "text/plain"),
        }).json()["id"]
        preview = client.post("/api/imports/preview", json={"file_id": file_id})
        assert preview.status_code == 200
        assert preview.json()["senders"] == ["Alice", "Bob"]
        confirmed = client.post("/api/imports/confirm", json={
            "file_id": file_id, "user_sender": "Alice", "object_sender": "Bob",
        })
        assert confirmed.status_code == 200
        assert confirmed.json()["imported_messages"] == 2
        detail = client.get(f"/api/conversations/{confirmed.json()['conversation_id']}").json()
        assert "用户=Alice；对象=Bob" in detail["messages"][0]["content"]
