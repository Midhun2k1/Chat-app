from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case


from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, ConversationParticipant, Message, User, MessageDelete
from app.utils.response_utils import success_response


router = APIRouter()


@router.post("/conversation/{user_id}")
def create_or_get_conversation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find existing 1-on-1 conversation between these two users
    existing_conv = db.query(ConversationParticipant.fld_conversation_id).filter(
        ConversationParticipant.fld_user_id.in_([current_user.fld_user_id, user_id])
    ).group_by(ConversationParticipant.fld_conversation_id).having(
        func.count(ConversationParticipant.fld_user_id) == 2
    ).first()

    if existing_conv:
        return success_response(data={"conversation_id": existing_conv.fld_conversation_id}, message="Conversation retrieved")

    # 2. If no existing conversation, create a new one
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

    return success_response(data={"conversation_id": new_conv.fld_conversation_Id}, message="Conversation created")


""" @router.post("/send-message/{conversation_id}")
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

    return {"message": "sent"} """


@router.get("/messages/{conversation_id}")
def get_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Subquery for messages deleted for the current user
    deleted_ids = db.query(MessageDelete.message_id).filter(
        MessageDelete.user_id == current_user.fld_user_id
    ).subquery()

    messages = db.query(Message).filter(
        Message.fld_conversation_id == conversation_id,
        ~Message.fld_message_id.in_(deleted_ids)
    ).order_by(Message.fld_created_at.desc()).offset(skip).limit(limit).all()

    # Format messages for the response
    formatted_messages = [
        {
            "message_id": msg.fld_message_id,
            "sender_id": msg.fld_sender_id,
            "message": msg.fld_message,
            "created_at": str(msg.fld_created_at),
            "is_read": msg.fld_is_read
        }
        for msg in messages
    ]
    return success_response(data={"messages": formatted_messages}, message="Messages fetched successfully")


@router.post("/mark-as-read/{conversation_id}")
def mark_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db.query(Message).filter(
        Message.fld_conversation_id == conversation_id,
        Message.fld_sender_id != current_user.fld_user_id,
        Message.fld_is_read == False
    ).update({"fld_is_read": True})

    db.commit()

    return success_response(message="Messages marked as read")


@router.get("/chats")
def get_user_chats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.fld_user_id

    #get latest message per conversation
    last_msg_subq = db.query(
        Message.fld_conversation_id,
        func.max(Message.fld_created_at).label("last_time")
    ).group_by(Message.fld_conversation_id).subquery()

    unread_subq = db.query(
        Message.fld_conversation_id,
        func.count(Message.fld_message_id).label("unread_count")
    ).filter(
        Message.fld_sender_id != user_id,
        Message.fld_is_read == False
    ).group_by(Message.fld_conversation_id).subquery()

    cp1 = aliased(ConversationParticipant)
    cp2 = aliased(ConversationParticipant)

    chats = db.query(
        cp1.fld_conversation_id,
        User.fld_user_id,
        User.fld_username,
        Message.fld_message,
        Message.fld_created_at,
        func.coalesce(unread_subq.c.unread_count, 0)
    ).join(
        cp2,
        (cp1.fld_conversation_id == cp2.fld_conversation_id) &
        (cp2.fld_user_id != user_id)
    ).join(
        User,
        User.fld_user_id == cp2.fld_user_id
    ).join(
        last_msg_subq,
        last_msg_subq.c.fld_conversation_id == cp1.fld_conversation_id
    ).join(
        Message,
        (Message.fld_conversation_id == last_msg_subq.c.fld_conversation_id) &
        (Message.fld_created_at == last_msg_subq.c.last_time)
    ).outerjoin(
        unread_subq,
        unread_subq.c.fld_conversation_id == cp1.fld_conversation_id
    ).filter(
        cp1.fld_user_id == user_id
    ).order_by(
        Message.fld_created_at.desc()
    ).all()

    result = []

    for chat in chats:
        result.append({
            "conversation_id": chat[0],
            "user_id": chat[1],
            "username": chat[2],
            "last_message": chat[3],
            "timestamp": str(chat[4]),
            "unread_count": chat[5]
        })

    return success_response(data={"chats": result}, message="User chats fetched successfully")