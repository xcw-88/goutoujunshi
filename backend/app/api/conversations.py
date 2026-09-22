from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Conversation, Person
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationRead, ConversationUpdate


router = APIRouter(prefix="/api/conversations", tags=["conversations"])
Database = Annotated[Session, Depends(get_db)]


def require_person(db: Session, person_id: str | None) -> None:
    if person_id and db.get(Person, person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")


def get_conversation_or_404(db: Session, conversation_id: str, detail: bool = False) -> Conversation:
    statement = select(Conversation).where(Conversation.id == conversation_id)
    if detail:
        statement = statement.options(selectinload(Conversation.messages))
    conversation = db.scalar(statement)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Database) -> list[Conversation]:
    return list(db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())))


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Database) -> Conversation:
    require_person(db, payload.person_id)
    conversation = Conversation(**payload.model_dump())
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Database) -> Conversation:
    return get_conversation_or_404(db, conversation_id, detail=True)


@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(
    conversation_id: str, payload: ConversationUpdate, db: Database
) -> Conversation:
    conversation = get_conversation_or_404(db, conversation_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"unbind_person"})
    if payload.unbind_person:
        changes["person_id"] = None
    require_person(db, changes.get("person_id"))
    for key, value in changes.items():
        setattr(conversation, key, value)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, db: Database) -> Response:
    conversation = get_conversation_or_404(db, conversation_id)
    db.delete(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

