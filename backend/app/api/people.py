from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Person, Relationship
from app.schemas.person import PersonCreate, PersonRead, PersonUpdate, RelationshipRead, RelationshipWrite


router = APIRouter(prefix="/api/people", tags=["people"])
Database = Annotated[Session, Depends(get_db)]


def get_person_or_404(db: Session, person_id: str) -> Person:
    person = db.scalar(
        select(Person)
        .options(selectinload(Person.relationship_profile))
        .where(Person.id == person_id)
    )
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    return person


@router.get("", response_model=list[PersonRead])
def list_people(db: Database) -> list[Person]:
    return list(
        db.scalars(select(Person).options(selectinload(Person.relationship_profile)).order_by(Person.updated_at.desc()))
    )


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Database) -> Person:
    person = Person(**payload.model_dump())
    db.add(person)
    db.commit()
    return get_person_or_404(db, person.id)


@router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: str, db: Database) -> Person:
    return get_person_or_404(db, person_id)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(person_id: str, payload: PersonUpdate, db: Database) -> Person:
    person = get_person_or_404(db, person_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, key, value)
    db.commit()
    return get_person_or_404(db, person_id)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: str, db: Database) -> Response:
    person = get_person_or_404(db, person_id)
    db.delete(person)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{person_id}/relationship", response_model=RelationshipRead)
def get_relationship(person_id: str, db: Database) -> Relationship:
    person = get_person_or_404(db, person_id)
    if person.relationship_profile is None:
        raise HTTPException(status_code=404, detail="relationship not found")
    return person.relationship_profile


@router.put("/{person_id}/relationship", response_model=RelationshipRead)
def upsert_relationship(person_id: str, payload: RelationshipWrite, db: Database) -> Relationship:
    person = get_person_or_404(db, person_id)
    relationship = person.relationship_profile
    if relationship is None:
        relationship = Relationship(person_id=person.id, **payload.model_dump())
        db.add(relationship)
    else:
        relationship.status = payload.status
        relationship.notes = payload.notes
    db.commit()
    db.refresh(relationship)
    return relationship

