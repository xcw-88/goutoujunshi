from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Memory, Person
from app.schemas.memory import MemoryContext, MemoryCreate, MemoryRead, MemoryUpdate


STABLE_SCOPES = ("user", "object", "relationship")


class MemoryNotFoundError(LookupError):
    pass


class PersonNotFoundError(LookupError):
    pass


class MemoryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _require_person(self, person_id: str | None) -> None:
        if person_id and self.session.get(Person, person_id) is None:
            raise PersonNotFoundError(person_id)

    def list(
        self,
        *,
        person_id: str | None = None,
        scope: str | None = None,
    ) -> list[Memory]:
        statement = select(Memory)
        if person_id is not None:
            statement = statement.where(Memory.person_id == person_id)
        if scope is not None:
            statement = statement.where(Memory.scope == scope)
        statement = statement.order_by(Memory.updated_at.desc())
        return list(self.session.scalars(statement))

    def create(self, payload: MemoryCreate) -> Memory:
        self._require_person(payload.person_id)
        memory = Memory(**payload.model_dump())
        self.session.add(memory)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def update(self, memory_id: str, payload: MemoryUpdate) -> Memory:
        memory = self.session.get(Memory, memory_id)
        if memory is None:
            raise MemoryNotFoundError(memory_id)
        changes = payload.model_dump(exclude_unset=True)
        candidate = MemoryCreate(
            person_id=memory.person_id,
            scope=memory.scope,  # type: ignore[arg-type]
            key=memory.key,
            value=changes.get("value", memory.value),
            confidence=changes.get("confidence", memory.confidence),
            source=changes.get("source", memory.source or "user_explicit"),
            occurred_at=changes.get("occurred_at", memory.occurred_at),
        )
        for key, value in candidate.model_dump().items():
            if key not in {"person_id", "scope", "key"}:
                setattr(memory, key, value)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def delete(self, memory_id: str) -> None:
        memory = self.session.get(Memory, memory_id)
        if memory is None:
            raise MemoryNotFoundError(memory_id)
        self.session.delete(memory)
        self.session.commit()

    def clear_person(self, person_id: str) -> int:
        result = self.session.execute(delete(Memory).where(Memory.person_id == person_id))
        self.session.commit()
        return int(result.rowcount or 0)

    def clear_all(self) -> int:
        result = self.session.execute(delete(Memory))
        self.session.commit()
        return int(result.rowcount or 0)

    def get_context(self, person_id: str, max_chars: int = 4000) -> MemoryContext:
        self._require_person(person_id)
        stable = list(
            self.session.scalars(
                select(Memory)
                .where(
                    Memory.scope.in_(STABLE_SCOPES),
                    (Memory.person_id == person_id) | (Memory.person_id.is_(None)),
                )
                .order_by(Memory.updated_at.desc())
            )
        )
        events = list(
            self.session.scalars(
                select(Memory)
                .where(Memory.person_id == person_id, Memory.scope == "event")
                .order_by(Memory.occurred_at.desc(), Memory.updated_at.desc())
                .limit(8)
            )
        )
        hypotheses = list(
            self.session.scalars(
                select(Memory)
                .where(Memory.person_id == person_id, Memory.scope == "hypothesis")
                .order_by(Memory.updated_at.desc())
                .limit(5)
            )
        )
        groups = {
            "confirmed_facts": [MemoryRead.model_validate(item) for item in stable],
            "events": [MemoryRead.model_validate(item) for item in events],
            "hypotheses": [MemoryRead.model_validate(item) for item in hypotheses],
        }
        while self._serialized_size(groups) > max_chars:
            if groups["hypotheses"]:
                groups["hypotheses"].pop()
            elif groups["events"]:
                groups["events"].pop()
            elif groups["confirmed_facts"]:
                groups["confirmed_facts"].pop()
            else:
                break
        return MemoryContext(**groups)

    @staticmethod
    def _serialized_size(groups: dict[str, list[MemoryRead]]) -> int:
        return len(
            json.dumps(
                {
                    key: [item.model_dump(mode="json") for item in values]
                    for key, values in groups.items()
                },
                ensure_ascii=False,
            )
        )

