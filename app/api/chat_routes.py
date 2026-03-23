from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, ConversationParticipant, Message, User


router = APIRouter()


@router.post("/conversation/{user_id}")
def create_or_get_conversation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find existing conversation
    conversations = db.query(ConversationParticipant).filter(
        ConversationParticipant.fld_user_id.in_([current_user.fld_user_id, user_id])
    ).all()

    #For now (simple): always create new
    new_conv = Conversation()
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)

    # add participants
    db.add_all([
        ConversationParticipant(
            fld_conversation_id=new_conv.fld_conversation_Id,
            fld_user_id=current_user.fld_user_id
        ),
        ConversationParticipant(
            fld_conversation_id=new_conv.fld_conversation_Id,
            fld_user_id=user_id
        )
    ])
    db.commit()

    return {"conversation_id": new_conv.fld_conversation_Id}


@router.post("/send-message/{conversation_id}")
def send_message(
    conversation_id: int,
    message: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_msg = Message(
        fld_conversation_id=conversation_id,
        fld_sender_id=current_user.fld_user_id,
        fld_message=message
    )

    db.add(new_msg)
    db.commit()

    return {"message": "sent"}


@router.get("/messages/{conversation_id}")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    messages = db.query(Message).filter(
        Message.fld_conversation_id == conversation_id
    ).order_by(Message.fld_created_at.asc()).all()

    return messages