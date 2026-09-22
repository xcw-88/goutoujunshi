from fastapi.testclient import TestClient


def test_people_relationship_and_conversation_crud(client: TestClient) -> None:
    created = client.post("/api/people", json={"display_name": "对象A", "notes": "同事"})
    assert created.status_code == 201
    person_id = created.json()["id"]

    relationship = client.put(
        f"/api/people/{person_id}/relationship",
        json={"status": "dating", "notes": "刚开始约会"},
    )
    assert relationship.status_code == 200
    assert relationship.json()["status"] == "dating"

    conversation = client.post(
        "/api/conversations", json={"title": "新对话", "person_id": person_id}
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]

    detail = client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"] == []

    unbound = client.patch(
        f"/api/conversations/{conversation_id}", json={"unbind_person": True}
    )
    assert unbound.status_code == 200
    assert unbound.json()["person_id"] is None

    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 204
    assert client.delete(f"/api/people/{person_id}").status_code == 204

