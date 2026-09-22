import sys
from pathlib import Path

from scripts.sync_core import sync


sync()
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


def client_with_env(*, authenticate=True, model_complete=None, **bindings):
    from fastapi.testclient import TestClient
    from worker import app

    bindings.setdefault("GOUTOU_ACCESS_PASSWORD", "test-only-password")
    bindings.setdefault("GOUTOU_SESSION_SECRET", "test-only-session-secret-32-characters")

    class Wrapper:
        async def __call__(self, scope, receive, send):
            scope["env"] = type("Bindings", (), bindings)()
            if model_complete is not None:
                scope["model_complete"] = model_complete
            await app(scope, receive, send)

    client = TestClient(Wrapper(), base_url="https://testserver")
    if authenticate:
        assert client.post("/api/auth/login", json={"password": bindings["GOUTOU_ACCESS_PASSWORD"]}).status_code == 200
    return client
