from tests.conftest import client_with_env
from tests.fake_bindings import D1Binding


def test_people_and_relationship_lifecycle() -> None:
    with client_with_env(DB=D1Binding()) as client:
        created = client.post("/api/people", json={"display_name": "小王", "notes": "朋友"})
        assert created.status_code == 201
        person = created.json()
        assert person["relationship_profile"] is None
        person_id = person["id"]
        assert client.get("/api/people").json()[0]["id"] == person_id
        assert client.patch(f"/api/people/{person_id}", json={"notes": "同事"}).json()["notes"] == "同事"
        assert client.put(f"/api/people/{person_id}/relationship", json={"status": "dating", "notes": ""}).json()["status"] == "dating"
        assert client.get(f"/api/people/{person_id}").json()["relationship_profile"]["status"] == "dating"
        assert client.delete(f"/api/people/{person_id}").status_code == 204
        assert client.get(f"/api/people/{person_id}").status_code == 404
