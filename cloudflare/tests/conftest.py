from scripts.sync_core import sync


sync()


def client_with_env(*, authenticate=True, **bindings):
    from fastapi.testclient import TestClient
    from src.worker import app

    bindings.setdefault("GOUTOU_ACCESS_PASSWORD", "test-only-password")
    bindings.setdefault("GOUTOU_SESSION_SECRET", "test-only-session-secret-32-characters")

    class Wrapper:
        async def __call__(self, scope, receive, send):
            scope["env"] = type("Bindings", (), bindings)()
            await app(scope, receive, send)

    client = TestClient(Wrapper(), base_url="https://testserver")
    if authenticate:
        assert client.post("/api/auth/login", json={"password": bindings["GOUTOU_ACCESS_PASSWORD"]}).status_code == 200
    return client
