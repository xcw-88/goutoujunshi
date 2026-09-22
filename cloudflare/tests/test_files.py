from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_cloud_file_library_is_disabled() -> None:
    with client_with_env(DB=D1Binding()) as client:
        assert client.get("/api/files").status_code == 410
        assert client.post("/api/files", files={"file": ("notes.txt", b"hello", "text/plain")}).status_code == 410
        assert client.get("/api/files/old/content").status_code == 410
        assert client.delete("/api/files/old").status_code == 410
