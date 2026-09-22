from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import build_engine, init_database
from app.models import Conversation, Memory, Message, Person, Relationship, Setting, UploadedFile


def test_domain_models_round_trip(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "models.db")
    init_database(engine)

    with Session(engine) as session:
        person = Person(display_name="对象A", notes="测试档案")
        person.relationship_profile = Relationship(status="dating", notes="稳定联系")
        person.memories.append(
            Memory(scope="object", key="mbti", value="INFP", source="user_report")
        )
        conversation = Conversation(title="关于对象A", person=person)
        conversation.messages.append(Message(role="user", content="测试消息"))
        upload = UploadedFile(
            original_name="chat.txt",
            stored_name="abc.txt",
            mime_type="text/plain",
            size=4,
            path="uploads/abc.txt",
        )
        setting = Setting(key="theme", value="system")
        session.add_all([conversation, upload, setting])
        session.commit()

        loaded = session.scalar(select(Person).where(Person.display_name == "对象A"))
        assert loaded is not None
        assert loaded.relationship_profile is not None
        assert loaded.relationship_profile.status == "dating"
        assert loaded.memories[0].scope == "object"
        assert conversation.messages[0].role == "user"
        assert session.get(UploadedFile, upload.id) is not None
        assert session.get(Setting, "theme").value == "system"  # type: ignore[union-attr]


def test_person_delete_cascades_profile_and_memory(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "cascade.db")
    init_database(engine)

    with Session(engine) as session:
        person = Person(display_name="待删除")
        person.relationship_profile = Relationship(status="former")
        person.memories.append(Memory(scope="event", key="breakup", value="已分开"))
        session.add(person)
        session.commit()
        person_id = person.id
        session.delete(person)
        session.commit()

        assert session.get(Person, person_id) is None
        assert session.scalar(select(Relationship)) is None
        assert session.scalar(select(Memory)) is None
