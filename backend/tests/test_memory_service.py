from sqlalchemy.orm import Session

from app.models import Person
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.services.memory_service import MemoryService


def test_memory_semantics_and_context_groups(session: Session) -> None:
    person = Person(display_name="对象A")
    session.add(person)
    session.commit()
    service = MemoryService(session)

    service.create(
        MemoryCreate(scope="user", key="mbti", value="INTJ", source="user_explicit")
    )
    event = service.create(
        MemoryCreate(
            person_id=person.id,
            scope="event",
            key="invitation",
            value="用户转述：对方接受了周末邀约",
            source="user_report",
        )
    )
    hypothesis = service.create(
        MemoryCreate(
            person_id=person.id,
            scope="hypothesis",
            key="interest",
            value="可能愿意继续了解",
            source="assistant_inference",
            confidence="medium",
        )
    )

    context = service.get_context(person.id)
    assert [item.id for item in context.events] == [event.id]
    assert [item.id for item in context.hypotheses] == [hypothesis.id]
    assert context.confirmed_facts[0].scope == "user"
    assert all(item.scope != "hypothesis" for item in context.confirmed_facts)

    updated = service.update(hypothesis.id, MemoryUpdate(confidence="low"))
    assert updated.confidence == "low"
    service.delete(event.id)
    assert service.list(scope="event") == []


def test_clear_person_and_all(session: Session) -> None:
    person = Person(display_name="对象A")
    session.add(person)
    session.commit()
    service = MemoryService(session)
    service.create(
        MemoryCreate(scope="user", key="goal", value="稳定关系", source="user_explicit")
    )
    service.create(
        MemoryCreate(
            person_id=person.id,
            scope="event",
            key="meeting",
            value="见面",
            source="user_report",
        )
    )

    assert service.clear_person(person.id) == 1
    assert len(service.list()) == 1
    assert service.clear_all() == 1
    assert service.list() == []

