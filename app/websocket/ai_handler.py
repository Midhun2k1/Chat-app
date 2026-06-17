import uuid
from datetime import datetime, timezone
from app.db.database import SessionLocal
from app.db.models import Message, ConversationParticipant, User
from app.services.ai_service import get_bot_reply
from app.services.embedding_service import embed_text
from app.websocket.manager import manager
from app.utils.time_utils import format_datetime_to_zulu

BOT_USERNAME = "pingbee-ai"


def _get_bot_user(db) -> User | None:
    return db.query(User).filter(
        User.fld_username == BOT_USERNAME,
        User.fld_is_bot == True
    ).first()


def _is_bot_participant(conversation_id: int, bot_user_id: int, db) -> bool:
    return db.query(ConversationParticipant).filter(
        ConversationParticipant.fld_conversation_id == conversation_id,
        ConversationParticipant.fld_user_id == bot_user_id
    ).first() is not None


def _build_context(conversation_id: int, bot_user_id: int, db, limit: int = 10) -> list[dict]:
    messages = (
        db.query(Message)
        .filter(
            Message.fld_conversation_id == conversation_id,
            Message.fld_is_deleted_for_everyone == False,
        )
        .order_by(Message.fld_created_at.desc())
        .limit(limit)
        .all()
    )
    messages = list(reversed(messages))
    return [
        {
            "role": "assistant" if msg.fld_sender_id == bot_user_id else "user",
            "content": msg.fld_message,
        }
        for msg in messages
    ]


async def handle_bot_reply(conversation_id: int):
    db = SessionLocal()
    print("came here =======1")
    try:
        bot = _get_bot_user(db)
        if not bot:
            print("[AI Handler] Bot user not found. Run setup_ai_features.py first.")
            return

        if not _is_bot_participant(conversation_id, bot.fld_user_id, db):
            return  # Bot is not in this conversation
        # here we need to call handle_typing() until reply send
        history = _build_context(conversation_id, bot.fld_user_id, db)
        reply_text = await get_bot_reply(history)

        bot_client_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        bot_message = Message(
            fld_conversation_id=conversation_id,
            fld_sender_id=bot.fld_user_id,
            fld_message=reply_text,
            fld_client_message_id=bot_client_id,
            fld_is_read=False,
            fld_created_at=now,
            fld_parent_message_id=None,
        )

        try:
            bot_message.fld_embedding = embed_text(reply_text)
        except Exception as emb_err:
            print(f"[AI Handler] Embedding failed (non-fatal): {emb_err}")

        db.add(bot_message)
        db.commit()
        db.refresh(bot_message)

        server_timestamp = format_datetime_to_zulu(now)

        # Sends via the same RECEIVE_MSG event the frontend already handles
        receive_msg = {
            "event": "RECEIVE_MSG",
            "payload": {
                "id": bot_client_id,
                "chatId": str(conversation_id),
                "text": reply_text,
                "senderId": str(bot.fld_user_id),
                "createdAt": server_timestamp,
                "serverTimestamp": server_timestamp,
                "isDeletedForEveryone": False,
                "isEdited": False,
                "replyTo": None,
                "isBot": True,  # Extra flag so frontend can style bot messages differently
            },
            "timestamp": server_timestamp,
        }

        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.fld_conversation_id == conversation_id
        ).all()

        for p in participants:
            if p.fld_user_id == bot.fld_user_id:
                continue
            await manager.send_personal_message(p.fld_user_id, receive_msg)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[AI Handler] Error: {e}")
    finally:
        db.close()
