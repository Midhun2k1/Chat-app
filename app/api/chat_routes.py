from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case
from datetime import datetime, timezone


from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, ConversationParticipant, Message, User, MessageDelete
from app.schemas.response import StandardResponse, ErrorResponse
from typing import List
from app.schemas.conversation import ConversationID, ChatList, ConversationCreateRequest, ChatUserDetailsRequest, UserDetail, ChatType
from app.schemas.message import MessageList, MessageFetchRequest, MarkAsReadRequest
from app.utils.response_utils import success_response, error_response
from app.utils.time_utils import format_datetime_to_zulu


router = APIRouter()

common_responses = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.post("/conversation", response_model=StandardResponse[ConversationID], responses=common_responses)
def create_or_get_conversation(
    request: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = request.user_id

    if user_id == current_user.fld_user_id:
        return error_response(message="You cannot start a conversation with yourself", code="INVALID_REQUEST", status_code=400)

    # 1. Find existing 1-on-1 conversation between these two users
    cp1 = aliased(ConversationParticipant)
    cp2 = aliased(ConversationParticipant)

    existing_conv = db.query(cp1.fld_conversation_id).join(
        cp2, cp1.fld_conversation_id == cp2.fld_conversation_id
    ).filter(
        cp1.fld_user_id == current_user.fld_user_id,
        cp2.fld_user_id == user_id
    ).first()

    if existing_conv:
        return {
            "success": True,
            "status": 200,
            "message": "Conversation retrieved",
            "data": {"conversation_id": existing_conv.fld_conversation_id}
        }

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

    return {
        "success": True,
        "status": 200,
        "message": "Conversation created",
        "data": {"conversation_id": new_conv.fld_conversation_Id}
    }


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


@router.post("/messages", response_model=StandardResponse[MessageList], responses=common_responses)
def get_messages(
    request: MessageFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation_id = request.conversation_id
    skip = request.skip
    limit = request.limit

    # Get message IDs deleted for the current user
    deleted_ids_rows = db.query(MessageDelete.message_id).filter(
        MessageDelete.user_id == current_user.fld_user_id
    ).all()
    deleted_ids = {row[0] for row in deleted_ids_rows}

    messages = db.query(Message).filter(
        Message.fld_conversation_id == conversation_id
    ).order_by(Message.fld_created_at.desc()).offset(skip).limit(limit).all()

    # Get parent messages for quotes to avoid N+1 queries
    parent_ids = [msg.parent_message_id for msg in messages if msg.parent_message_id]
    parent_msgs_dict = {}
    if parent_ids:
        parent_msgs = db.query(Message).filter(Message.client_message_id.in_(parent_ids)).all()
        parent_msgs_dict = {pm.client_message_id: pm for pm in parent_msgs}

    # Format messages for the response
    formatted_messages = [
        {
            "message_id": msg.client_message_id,
            "sender_id": msg.fld_sender_id,
            "message": msg.fld_message,
            "created_at": format_datetime_to_zulu(msg.fld_created_at),
            "is_read": msg.fld_is_read,
            "is_deleted_for_everyone": msg.fld_is_deleted_for_everyone,
            "is_delete_for_me": msg.fld_message_id in deleted_ids,
            "reply_to": parent_msgs_dict[msg.parent_message_id].client_message_id if msg.parent_message_id and msg.parent_message_id in parent_msgs_dict else None,
            "is_edited": getattr(msg, "fld_is_edited", False)
        }
        for msg in messages
    ]
    return {
        "success": True,
        "status": 200,
        "message": "Messages fetched successfully",
        "data": {"messages": formatted_messages}
    }


@router.post("/mark-as-read", response_model=StandardResponse[None], responses=common_responses)
def mark_as_read(
    request: MarkAsReadRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    conversation_id = request.conversation_id
    db.query(Message).filter(
        Message.fld_conversation_id == conversation_id,
        Message.fld_sender_id != current_user.fld_user_id,
        Message.fld_is_read == False
    ).update({"fld_is_read": True})

    db.commit()

    return {
        "success": True,
        "status": 200,
        "message": "Messages marked as read"
    }


@router.get("/chats", response_model=StandardResponse[ChatList], responses=common_responses)
def get_user_chats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.fld_user_id

    # Subquery: Latest message per conversation
    last_msg_subq = db.query(
        Message.fld_conversation_id,
        func.max(Message.fld_created_at).label("last_time")
    ).group_by(Message.fld_conversation_id).subquery()

    # Subquery: Unread count per conversation for this user
    unread_subq = db.query(
        Message.fld_conversation_id,
        func.count(Message.fld_message_id).label("unread_count")
    ).filter(
        Message.fld_sender_id != user_id,
        Message.fld_is_read == False
    ).group_by(Message.fld_conversation_id).subquery()

    # Query conversations current_user is participant in, with latest message and unread count
    user_convs = db.query(
        Conversation.fld_conversation_Id,
        Message.fld_message.label("last_message_text"),
        Message.fld_created_at.label("last_message_time"),
        User.fld_username.label("last_message_sender_username"),
        func.coalesce(unread_subq.c.unread_count, 0).label("unread_count")
    ).join(
        ConversationParticipant,
        ConversationParticipant.fld_conversation_id == Conversation.fld_conversation_Id
    ).join(
        last_msg_subq,
        last_msg_subq.c.fld_conversation_id == Conversation.fld_conversation_Id
    ).join(
        Message,
        (Message.fld_conversation_id == last_msg_subq.c.fld_conversation_id) &
        (Message.fld_created_at == last_msg_subq.c.last_time)
    ).join(
        User,
        User.fld_user_id == Message.fld_sender_id
    ).outerjoin(
        unread_subq,
        unread_subq.c.fld_conversation_id == Conversation.fld_conversation_Id
    ).filter(
        ConversationParticipant.fld_user_id == user_id
    ).order_by(
        Message.fld_created_at.desc()
    ).all()

    if not user_convs:
        return {
            "success": True,
            "status": 200,
            "message": "User chats fetched successfully",
            "data": {"chats": []}
        }

    # Fetch all participants in these conversations in a single batch query
    conv_ids = [c.fld_conversation_Id for c in user_convs]
    all_participants = db.query(
        ConversationParticipant.fld_conversation_id,
        User.fld_user_id,
        User.fld_username,
        User.fld_firstname,
        User.fld_lastname,
        User.fld_avatar_url
    ).join(
        User,
        User.fld_user_id == ConversationParticipant.fld_user_id
    ).filter(
        ConversationParticipant.fld_conversation_id.in_(conv_ids)
    ).all()

    # Group participants by conversation ID in memory
    from collections import defaultdict
    participants_by_conv = defaultdict(list)
    for p in all_participants:
        participants_by_conv[p.fld_conversation_id].append({
            "user_id": p.fld_user_id,
            "username": p.fld_username,
            "firstname": p.fld_firstname,
            "lastname": p.fld_lastname,
            "avatar_url": p.fld_avatar_url
        })

    result = []
    for chat in user_convs:
        cid = chat.fld_conversation_Id
        parts = participants_by_conv[cid]

        user_ids_str = [str(p["user_id"]) for p in parts]
        chat_type = ChatType.INDIVIDUAL if len(parts) == 2 else ChatType.GROUP

        # Determine chat display name and avatar url
        chat_avatar = None
        if chat_type == ChatType.INDIVIDUAL:
            other_part = next((p for p in parts if p["user_id"] != user_id), None)
            if other_part:
                chat_name = f"{other_part['firstname']} {other_part['lastname']}".strip()
                chat_avatar = other_part["avatar_url"]
            else:
                chat_name = "Saved Messages"
                me_part = next((p for p in parts if p["user_id"] == user_id), None)
                if me_part:
                    chat_avatar = me_part["avatar_url"]
        else:
            other_names = [p["firstname"] for p in parts if p["user_id"] != user_id]
            chat_name = ", ".join(other_names) if other_names else "Group Chat"

        updated_at_str = format_datetime_to_zulu(chat.last_message_time) if chat.last_message_time else format_datetime_to_zulu(datetime.now(timezone.utc))

        result.append({
            "id": str(cid),
            "name": chat_name,
            "type": chat_type,
            "unread_count": chat.unread_count,
            "last_message_text": chat.last_message_text,
            "updated_at": updated_at_str,
            "avatar_url": chat_avatar,
            "participants": {
                "userIDs": user_ids_str
            },
            "lastMessageSentUsername": chat.last_message_sender_username
        })

    return {
        "success": True,
        "status": 200,
        "message": "User chats fetched successfully",
        "data": {"chats": result}
    }


@router.post("/chat-users-details", response_model=StandardResponse[List[UserDetail]], responses=common_responses)
def get_chat_users_details(
    request: ChatUserDetailsRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        conv_id = int(request.chatId)
    except ValueError:
        return error_response(message="Invalid chat ID format", code="INVALID_REQUEST", status_code=400)

    # Verify that the current_user is a participant in this conversation
    is_participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.fld_conversation_id == conv_id,
        ConversationParticipant.fld_user_id == current_user.fld_user_id
    ).first()

    if not is_participant:
        return error_response(message="Unauthorized access to chat details", code="UNAUTHORIZED", status_code=403)

    # Query details of all participants
    participants = db.query(User).join(
        ConversationParticipant,
        ConversationParticipant.fld_user_id == User.fld_user_id
    ).filter(
        ConversationParticipant.fld_conversation_id == conv_id
    ).all()

    user_details = []
    for user in participants:
        user_details.append({
            "userId": str(user.fld_user_id),
            "name": f"{user.fld_firstname} {user.fld_lastname}".strip(),
            "is_me": user.fld_user_id == current_user.fld_user_id,
            "username": user.fld_username,
            "first_name": user.fld_firstname,
            "last_name": user.fld_lastname,
            "email": user.fld_email,
            "avatar_url": None,
            "phone_number": user.fld_phone
        })

    return {
        "success": True,
        "status": 200,
        "message": "Chat user details fetched successfully",
        "data": user_details
    }

