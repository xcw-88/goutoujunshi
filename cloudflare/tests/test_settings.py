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
