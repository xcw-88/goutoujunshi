from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_import_preview_and_confirm_speaker_mapping() -> None:
    database = D1Binding()
    source = "Alice: 你好\nBob: 你好啊".encode()
    with client_with_env(DB=database) as client:
        preview = client.post("/api/imports/preview", files={"file": ("chat.txt", source, "text/plain")})
        assert preview.status_code == 200
        assert preview.json()["senders"] == ["Alice", "Bob"]
        confirmed = client.post("/api/imports/confirm", files={"file": ("chat.txt", source, "text/plain")}, data={
            "payload": '{"user_sender":"Alice","object_sender":"Bob"}',
        })
        assert confirmed.status_code == 200
        assert confirmed.json()["imported_messages"] == 2
        detail = client.get(f"/api/conversations/{confirmed.json()['conversation_id']}").json()
        assert "用户=Alice；对象=Bob" in detail["messages"][0]["content"]
        assert "file_id" not in detail["messages"][0]["metadata_json"]
