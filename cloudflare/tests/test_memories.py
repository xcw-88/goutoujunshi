from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_memory_semantics_and_context() -> None:
    with client_with_env(DB=D1Binding()) as client:
        person_id = client.post("/api/people", json={"display_name": "A"}).json()["id"]
        fact = client.post("/api/memories", json={
            "person_id": person_id, "scope": "object", "key": "preference", "value": "tea", "source": "user_report",
        })
        assert fact.status_code == 201
        memory_id = fact.json()["id"]
        assert client.get(f"/api/memories/context/{person_id}").json()["confirmed_facts"][0]["id"] == memory_id
        assert client.patch(f"/api/memories/{memory_id}", json={"value": "coffee"}).json()["value"] == "coffee"
        invalid = client.post("/api/memories", json={
            "person_id": person_id, "scope": "object", "key": "guess", "value": "x", "source": "assistant_inference",
        })
        assert invalid.status_code == 422
        assert client.delete(f"/api/memories/{memory_id}").status_code == 204
        assert client.get(f"/api/memories?person_id={person_id}").json() == []
