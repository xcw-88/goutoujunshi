from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_cloud_settings_keep_key_in_secret() -> None:
    with client_with_env(DB=D1Binding(), GOUTOU_API_BASE="https://api.example/v1", GOUTOU_MODEL="test-model", GOUTOU_TEMPERATURE="0.7", GOUTOU_MAX_TOKENS="1200", GOUTOU_API_KEY="secret-key") as client:
        initial = client.get("/api/settings").json()
        assert initial["api_key_configured"] is True
        assert "secret-key" not in str(initial)
        assert client.patch("/api/settings", json={"api_key": "leak"}).status_code == 400
        assert client.patch("/api/settings", json={"base_url": "http://insecure.example"}).status_code == 400
        updated = client.patch("/api/settings", json={"model": "other-model"})
        assert updated.status_code == 200
        assert updated.json()["model"] == "other-model"


def test_gemini_uses_its_own_secret_without_exposing_either_key() -> None:
    with client_with_env(
        DB=D1Binding(), GOUTOU_API_BASE="https://api.openai.com/v1",
        GOUTOU_MODEL="gpt-4.1-mini", GOUTOU_API_KEY="openai-secret",
        GOUTOU_GEMINI_API_KEY="gemini-secret",
    ) as client:
        switched = client.patch("/api/settings", json={
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "model": "gemini-3.8-flash",
        })
        assert switched.status_code == 200
        assert switched.json()["api_key_configured"] is True
        assert "gemini-secret" not in str(switched.json())
        assert "openai-secret" not in str(switched.json())
        restored = client.patch("/api/settings", json={"base_url": "https://api.openai.com/v1"})
        assert restored.json()["api_key_configured"] is True


def test_gemini_key_status_is_false_when_only_generic_key_is_configured() -> None:
    with client_with_env(DB=D1Binding(), GOUTOU_API_BASE="https://api.openai.com/v1", GOUTOU_MODEL="gpt-4.1-mini", GOUTOU_API_KEY="openai-secret") as client:
        response = client.patch("/api/settings", json={"base_url": "https://generativelanguage.googleapis.com/v1beta/openai"})
        assert response.json()["api_key_configured"] is False


def test_spoofed_gemini_hostname_cannot_use_gemini_secret() -> None:
    with client_with_env(DB=D1Binding(), GOUTOU_API_BASE="https://api.openai.com/v1", GOUTOU_MODEL="gpt-4.1-mini", GOUTOU_GEMINI_API_KEY="gemini-secret") as client:
        response = client.patch("/api/settings", json={"base_url": "https://generativelanguage.googleapis.com.evil.example/v1beta/openai"})
        assert response.json()["api_key_configured"] is False
