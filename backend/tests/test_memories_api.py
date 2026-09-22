from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Person


def test_memory_crud_api(client: TestClient, session: Session) -> None:
    person = Person(display_name="对象A")
    session.add(person)
    session.commit()

    created = client.post(
        "/api/memories",
        json={
            "person_id": person.id,
            "scope": "hypothesis",
            "key": "intent",
            "value": "可能希望慢一点",
            "source": "assistant_inference",
            "confidence": "medium",
        },
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    context = client.get(f"/api/memories/context/{person.id}")
    assert context.status_code == 200
    assert context.json()["confirmed_facts"] == []
    assert context.json()["hypotheses"][0]["id"] == memory_id

    updated = client.patch(f"/api/memories/{memory_id}", json={"confidence": "low"})
    assert updated.status_code == 200
    assert updated.json()["confidence"] == "low"

    deleted = client.delete(f"/api/memories/{memory_id}")
    assert deleted.status_code == 204


def test_rejects_inference_as_object_fact(client: TestClient, session: Session) -> None:
    person = Person(display_name="对象A")
    session.add(person)
    session.commit()

    response = client.post(
        "/api/memories",
        json={
            "person_id": person.id,
            "scope": "object",
            "key": "personality",
            "value": "回避型",
            "source": "assistant_inference",
        },
    )
    assert response.status_code == 422
