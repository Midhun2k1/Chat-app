from datetime import datetime
from sqlalchemy.orm import Session
from app.websocket.manager import manager
from app.db.models import Message, ConversationParticipant, MessageDelete
from app.schemas.websocket import (
    SendMessagePayload, TypingPayload, MessageStatusPayload, PresencePayload,
    EditMessagePayload, DeleteMessagePayload, WsServerMessage,
    AckSendMessagePayload, ReceiveMessagePayload, TypingBroadcastPayload,
    MessageStatusBroadcastPayload, PresenceBroadcastPayload,
    AckEditMessagePayload, ReceiveEditMessagePayload,
    AckDeleteMessagePayload, ReceiveDeleteMessagePayload, ErrorPayload
)



# TO SEND MESSAGE
async def handle_send_message(user_id: int, payload: SendMessagePayload, db: Session):
    try:
        conversation_id = payload.chatId
        text = payload.text
        client_msg_id = payload.id

        new_message = Message(
            fld_conversation_id=conversation_id,
            fld_sender_id=user_id,
            fld_message=text,
            fld_created_at=datetime.utcnow(),
            fld_is_read=False,
            client_message_id=client_msg_id
        )

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        server_timestamp = datetime.utcnow().isoformat()

        # Construct ACK message
        ack_msg = WsServerMessage(
            event="ACK_SEND_MSG",
            payload=AckSendMessagePayload(id=client_msg_id, serverTimestamp=server_timestamp),
            timestamp=server_timestamp
        )

        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json(ack_msg.model_dump())

        # Get participants
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.fld_conversation_id == conversation_id
        ).all()

        # Ensure we only send to unique users to avoid duplicates
        unique_participant_ids = {p.fld_user_id for p in participants}

        # Construct Broadcast message
        receive_msg = WsServerMessage(
            event="RECEIVE_MSG",
            payload=ReceiveMessagePayload(
                id=client_msg_id,
                chatId=str(conversation_id),
                text=text,
                senderId=str(user_id),
                createdAt=new_message.fld_created_at.isoformat(),
                serverTimestamp=server_timestamp,
                isDeletedForEveryone=new_message.fld_is_deleted_for_everyone
            ),
            timestamp=server_timestamp
        )

        for target_uid in unique_participant_ids:
            if target_uid == user_id: # Skip sending the message back to the sender
                continue

            target_sockets = manager.active_connections.get(target_uid, [])
            for ws in target_sockets:
                await ws.send_json(receive_msg.model_dump())

    except Exception as e:
        print("SEND_MSG ERROR:", e)



# TYPING INDICATOR
async def handle_typing(user_id: int, payload: TypingPayload):
    try:
        chat_id = payload.chatId
        is_typing = payload.isTyping

        server_timestamp = datetime.utcnow().isoformat()
        typing_msg = WsServerMessage(
            event="TYPING",
            payload=TypingBroadcastPayload(
                chatId=str(chat_id),
                userId=str(user_id),
                isTyping=is_typing
            ),
            timestamp=server_timestamp
        )

        for uid, sockets in manager.active_connections.items():
            if uid != user_id:
                for ws in sockets:
                    await ws.send_json(typing_msg.model_dump())

    except Exception as e:
        print("TYPING ERROR:", e)



# MESSAGE STATUS (DELIVERED / READ)
async def handle_message_status(user_id: int, payload: MessageStatusPayload, db: Session):
    try:
        message_id = payload.messageId
        status = payload.status

        if status == "read":
            target_message = db.query(Message).filter(Message.client_message_id == message_id).first()

            if target_message:
                db.query(Message).filter(
                    Message.fld_conversation_id == target_message.fld_conversation_id,
                    Message.fld_sender_id != user_id,
                    Message.fld_is_read == False,
                    Message.fld_created_at <= target_message.fld_created_at
                ).update({"fld_is_read": True})

                db.commit()

        server_timestamp = datetime.utcnow().isoformat()
        status_msg = WsServerMessage(
            event="MSG_STATUS",
            payload=MessageStatusBroadcastPayload(
                messageId=str(message_id),
                status=status
            ),
            timestamp=server_timestamp
        )

        for sockets in manager.active_connections.values():
            for ws in sockets:
                await ws.send_json(status_msg.model_dump())

    except Exception as e:
        print("MSG_STATUS ERROR:", e)



# PRESENCE (ONLINE / OFFLINE MANUAL SIGNAL)
async def handle_presence(user_id: int, payload: PresencePayload):
    try:
        status = payload.status

        server_timestamp = datetime.utcnow().isoformat()
        presence_msg = WsServerMessage(
            event="PRESENCE",
            payload=PresenceBroadcastPayload(
                userId=str(user_id),
                status=status
            ),
            timestamp=server_timestamp
        )

        for uid, sockets in manager.active_connections.items():
            if uid != user_id:
                for ws in sockets:
                    await ws.send_json(presence_msg.model_dump())

    except Exception as e:
        print("PRESENCE ERROR:", e)



# TO EDIT MESSAGE
async def handle_edit_message(user_id: int, payload: EditMessagePayload, db: Session):
    try:
        message_id = payload.id
        new_text = payload.text
        edited_at = payload.editedAt

        message = db.query(Message).filter(
            Message.client_message_id == message_id,
            Message.fld_sender_id == user_id
        ).first()

        if not message:
            return

        # Construction server timestamp
        server_timestamp = datetime.utcnow().isoformat()

        # Only sender can edit
        if message.fld_sender_id != user_id:
            error_msg = WsServerMessage(
                event="ERROR",
                payload=ErrorPayload(message="You can only edit your own messages."),
                timestamp=server_timestamp
            )
            sender_sockets = manager.active_connections.get(user_id, [])
            for ws in sender_sockets:
                await ws.send_json(error_msg.model_dump())
            return

        message.fld_message = new_text
        db.commit()

        # ACK sender
        ack_msg = WsServerMessage(
            event="ACK_EDIT_MSG",
            payload=AckEditMessagePayload(id=str(message_id), editedAt=server_timestamp),
            timestamp=server_timestamp
        )
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json(ack_msg.model_dump())

        # Broadcast edit
        receive_edit_msg = WsServerMessage(
            event="RECEIVE_EDIT_MSG",
            payload=ReceiveEditMessagePayload(
                id=str(message_id),
                text=new_text,
                editedAt=str(edited_at) if edited_at else server_timestamp
            ),
            timestamp=server_timestamp
        )

        # Get participants of this conversation
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.fld_conversation_id == message.fld_conversation_id
        ).all()
        unique_participant_ids = {p.fld_user_id for p in participants}

        for target_uid in unique_participant_ids:
            if target_uid == user_id: # Skip the sender
                continue

            target_sockets = manager.active_connections.get(target_uid, [])
            for ws in target_sockets:
                await ws.send_json(receive_edit_msg.model_dump())

    except Exception as e:
        print("EDIT_MSG ERROR:", e)



# DELETE MESSAGE
async def handle_delete_message(user_id: int, payload: DeleteMessagePayload, db: Session):
    try:
        message_id = payload.id
        delete_type = payload.deleteType
        deleted_at = payload.deletedAt

        message = db.query(Message).filter(
            Message.client_message_id == message_id
        ).first()

        if not message:
            return

        server_timestamp = datetime.utcnow().isoformat()

        if delete_type == "deleteForEveryone":
            if message.fld_sender_id != user_id:
                error_msg = WsServerMessage(
                    event="ERROR",
                    payload=ErrorPayload(message="You can only delete your own messages for everyone."),
                    timestamp=server_timestamp
                )
                sender_sockets = manager.active_connections.get(user_id, [])
                for ws in sender_sockets:
                    await ws.send_json(error_msg.model_dump())
                return

            message.fld_is_deleted_for_everyone = True
            db.commit()

        elif delete_type == "deleteForMe":
            new_delete = MessageDelete(
                message_id=message.fld_message_id,
                user_id=user_id
            )
            db.add(new_delete)
            db.commit()

        # ACK sender
        ack_msg = WsServerMessage(
            event="ACK_DELETE_MSG",
            payload=AckDeleteMessagePayload(id=str(message_id), deletedAt=server_timestamp),
            timestamp=server_timestamp
        )
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json(ack_msg.model_dump())

        # Broadcast delete ONLY for 'deleteForEveryone'
        if delete_type == "deleteForEveryone":
            receive_delete_msg = WsServerMessage(
                event="RECEIVE_DELETE_MSG",
                payload=ReceiveDeleteMessagePayload(
                    id=str(message_id),
                    deleteType=delete_type,
                    deletedAt=str(deleted_at) if deleted_at else server_timestamp
                ),
                timestamp=server_timestamp
            )

            # Get participants of this conversation
            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.fld_conversation_id == message.fld_conversation_id
            ).all()
            unique_participant_ids = {p.fld_user_id for p in participants}

            for target_uid in unique_participant_ids:
                if target_uid == user_id: # Skip the sender
                    continue

                target_sockets = manager.active_connections.get(target_uid, [])
                for ws in target_sockets:
                    await ws.send_json(receive_delete_msg.model_dump())

    except Exception as e:
        print("DELETE_MSG ERROR:", e)