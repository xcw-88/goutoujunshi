from fastapi.testclient import TestClient

from src.worker import app


def test_cloudflare_health_route() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "runtime": "cloudflare-workers"}
