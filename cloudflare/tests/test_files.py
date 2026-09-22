from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding, R2Binding


def test_file_round_trip_and_validation() -> None:
    bucket = R2Binding()
    with client_with_env(DB=D1Binding(), UPLOADS=bucket) as client:
        invalid = client.post("/api/files", files={"file": ("page.html", b"bad", "text/html")})
        assert invalid.status_code == 400
        upload = client.post("/api/files", files={"file": ("notes.txt", b"hello", "text/plain")})
        assert upload.status_code == 201
        file_id = upload.json()["id"]
        assert client.get("/api/files").json()[0]["id"] == file_id
        content = client.get(f"/api/files/{file_id}/content")
        assert content.content == b"hello"
        assert content.headers["x-content-type-options"] == "nosniff"
        assert client.delete(f"/api/files/{file_id}").status_code == 204
        assert not bucket.objects
