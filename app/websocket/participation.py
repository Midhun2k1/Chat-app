from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.websocket.manager import manager
from app.db.models import ConversationParticipant
from app.utils.time_utils import format_datetime_to_zulu
from app.schemas.websocket import WsServerMessage, ErrorPayload


async def verify_participant(user_id: int, conversation_id: int, db: Session) -> bool:
    """Return True if user_id is a participant of conversation_id.
    Sends an ERROR message to the user if not.
    """
    participants = db.query(ConversationParticipant).filter(
        ConversationParticipant.fld_conversation_id == conversation_id
    ).all()
    if user_id not in {p.fld_user_id for p in participants}:
        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))
        error_msg = WsServerMessage(
            event="ERROR",
            payload=ErrorPayload(message="You are not a participant in this conversation."),
            timestamp=server_timestamp,
        )
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json(error_msg.model_dump())
        return False
    return True
