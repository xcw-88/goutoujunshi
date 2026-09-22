from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.providers.dependencies import get_model_provider
from app.providers.fake import FakeModelProvider


def test_upload_download_and_delete(client: TestClient) -> None:
    response = client.post(
        "/api/files",
        files={"file": ("../chat.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["original_name"] == "chat.txt"
    assert ".." not in payload["stored_name"]

    content = client.get(f"/api/files/{payload['id']}/content")
    assert content.status_code == 200
    assert content.content == b"hello"
    assert client.delete(f"/api/files/{payload['id']}").status_code == 204


def test_rejects_executable_and_oversize(client: TestClient) -> None:
    executable = client.post(
        "/api/files", files={"file": ("bad.exe", b"no", "application/octet-stream")}
    )
    assert executable.status_code == 400

    oversize = client.post(
        "/api/files",
        files={"file": ("huge.txt", b"x" * (20 * 1024 * 1024 + 1), "text/plain")},
    )
    assert oversize.status_code == 400


def test_uploaded_image_becomes_multimodal_message(client: TestClient) -> None:
    fake = FakeModelProvider("看到了截图。")
    app.dependency_overrides[get_model_provider] = lambda: fake
    upload = client.post(
        "/api/files",
        files={"file": ("screen.png", b"fake-png", "image/png")},
    ).json()
    conversation = client.post("/api/conversations", json={}).json()

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation["id"],
            "message": "只根据截图可见内容分析",
            "file_ids": [upload["id"]],
        },
    )
    assert response.status_code == 200
    content = fake.calls[0][-1]["content"]
    assert content[0] == {"type": "text", "text": "只根据截图可见内容分析"}
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
