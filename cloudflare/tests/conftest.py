from scripts.sync_core import sync


sync()


def client_with_env(**bindings):
    from fastapi.testclient import TestClient
    from src.worker import app

    class Wrapper:
        async def __call__(self, scope, receive, send):
            scope["env"] = type("Bindings", (), bindings)()
            await app(scope, receive, send)

    return TestClient(Wrapper())
