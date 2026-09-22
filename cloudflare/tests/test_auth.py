from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_api_requires_login_and_rejects_cross_origin() -> None:
    with client_with_env(authenticate=False, DB=D1Binding()) as client:
        assert client.get("/api/people").status_code == 401
        assert client.get("/api/auth/session").json() == {"authenticated": False}
        assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"password": "test-only-password"}).status_code == 200
        assert client.get("/api/people").status_code == 200
        assert client.post("/api/people", json={"display_name": "A"}, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/people").status_code == 401


def test_missing_secret_fails_closed() -> None:
    with client_with_env(authenticate=False, DB=D1Binding(), GOUTOU_SESSION_SECRET="") as client:
        assert client.get("/api/people").status_code == 503
        assert client.post("/api/auth/login", json={"password": "test-only-password"}).status_code == 503
