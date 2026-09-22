from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_conversation_lifecycle() -> None:
    with client_with_env(DB=D1Binding()) as client:
        person = client.post("/api/people", json={"display_name": "A"}).json()
        created = client.post("/api/conversations", json={"title": "Hi", "person_id": person["id"]})
        assert created.status_code == 201
        conversation_id = created.json()["id"]
        assert client.get(f"/api/conversations/{conversation_id}").json()["messages"] == []
        assert client.patch(f"/api/conversations/{conversation_id}", json={"unbind_person": True}).json()["person_id"] is None
        assert client.get("/api/conversations").json()[0]["id"] == conversation_id
        assert client.delete(f"/api/conversations/{conversation_id}").status_code == 204
        assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
