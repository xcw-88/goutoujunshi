from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting
from app.services.settings_service import reset_runtime_secrets


def test_settings_mask_api_key_and_persist_only_non_secret(
    client: TestClient, session: Session
) -> None:
    reset_runtime_secrets()
    response = client.patch(
        "/api/settings",
        json={
            "base_url": "https://example.test/v1",
            "api_key": "sk-test-secret-9F3A",
            "model": "example-model",
            "temperature": 0.4,
            "max_tokens": 900,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_configured"] is True
    assert payload["api_key_masked"].endswith("9F3A")
    assert "test-secret" not in response.text

    stored = {item.key: item.value for item in session.scalars(select(Setting))}
    assert stored["model"] == "example-model"
    assert all("secret" not in value for value in stored.values())
    assert "api_key" not in stored
    reset_runtime_secrets()


def test_clear_runtime_api_key(client: TestClient) -> None:
    reset_runtime_secrets()
    client.patch("/api/settings", json={"api_key": "temporary-key"})
    response = client.patch("/api/settings", json={"clear_api_key": True})
    assert response.json()["api_key_configured"] is False
    assert response.json()["api_key_masked"] is None
    reset_runtime_secrets()
