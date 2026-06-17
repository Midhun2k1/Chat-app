from datetime import datetime, timezone
import asyncio
from sqlalchemy.orm import Session
from .participation import verify_participant
from app.websocket.manager import manager
from app.db.models import Message, ConversationParticipant, MessageDelete
from app.utils.time_utils import format_datetime_to_zulu, parse_datetime
from app.websocket.ai_handler import handle_bot_reply
from app.services.embedding_service import embed_text
from app.schemas.websocket import (
    SendMessagePayload, TypingPayload, MessageStatusPayload, PresencePayload,
    EditMessagePayload, WsServerMessage,
    AckSendMessagePayload, ReceiveMessagePayload, TypingBroadcastPayload,
    MessageStatusBroadcastPayload, PresenceBroadcastPayload,
    AckEditMessagePayload, ReceiveEditMessagePayload,
    ErrorPayload,
    DeleteMultipleMessagesPayload, AckDeleteMultipleMessagesPayload, AckDeleteMultipleMessagesItem,
    ReceiveDeleteMultipleMessagesPayload, ReceiveDeleteMultipleMessagesItem,

)



# TO SEND MESSAGE
async def handle_send_message(user_id: int, payload: SendMessagePayload, db: Session):
    try:
        conversation_id = payload.chatId
        text = payload.text
        client_msg_id = payload.id
        parent_msg_id = payload.replyTo

        if not await verify_participant(user_id, conversation_id, db):
            return

        new_message = Message(
            fld_conversation_id=conversation_id,
            fld_sender_id=user_id,
            fld_message=text,
            fld_created_at=parse_datetime(payload.createdAt),
            fld_is_read=False,
            fld_client_message_id=client_msg_id,
            fld_parent_message_id=parent_msg_id
        )

        # Generate semantic embedding (for search feature — fails silently if not ready)
        try:
            new_message.fld_embedding = embed_text(text)
        except Exception as emb_err:
            print(f"[Embedding] Failed (non-fatal): {emb_err}")

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))

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

        parent_msg = None
        if parent_msg_id:
            parent_msg = db.query(Message).filter(Message.fld_client_message_id == parent_msg_id).first()

        # Construct Broadcast message
        receive_msg = WsServerMessage(
            event="RECEIVE_MSG",
            payload=ReceiveMessagePayload(
                id=client_msg_id,
                chatId=str(conversation_id),
                text=text,
                senderId=str(user_id),
                createdAt=format_datetime_to_zulu(new_message.fld_created_at),
                serverTimestamp=server_timestamp,
                isDeletedForEveryone=new_message.fld_is_deleted_for_everyone,
                isEdited=new_message.fld_is_edited,
                replyTo=parent_msg.fld_client_message_id if parent_msg else None
            ),
            timestamp=server_timestamp
        )

        for target_uid in unique_participant_ids:
            if target_uid == user_id: # Skip sending the message back to the sender
                continue

            target_sockets = manager.active_connections.get(target_uid, [])
            for ws in target_sockets:
                await ws.send_json(receive_msg.model_dump())

        # Trigger bot reply in background — user gets ACK immediately, bot replies ~1-2s later
        asyncio.create_task(
            handle_bot_reply(conversation_id=conversation_id)
        )

    except Exception as e:
        print("SEND_MSG ERROR:", e)



# TYPING INDICATOR
async def handle_typing(user_id: int, payload: TypingPayload, db: Session):
    try:
        chat_id = payload.chatId
        is_typing = payload.isTyping

        # Verify sender participation
        if not await verify_participant(user_id, chat_id, db):
            return

        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))
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
            target_message = db.query(Message).filter(Message.fld_client_message_id == message_id).first()

            # Verify participant involvement
            if target_message and not await verify_participant(user_id, target_message.fld_conversation_id, db):
                return

            if target_message:
                db.query(Message).filter(
                    Message.fld_conversation_id == target_message.fld_conversation_id,
                    Message.fld_sender_id != user_id,
                    Message.fld_is_read == False,
                    Message.fld_created_at <= target_message.fld_created_at
                ).update({"fld_is_read": True})

                db.commit()

        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))
        status_msg = WsServerMessage(
            event="MSG_STATUS",
            payload=MessageStatusBroadcastPayload(
                messageId=str(message_id),
                status=status
            ),
            timestamp=server_timestamp
        )

        for uid, sockets in manager.active_connections.items():
            if uid != user_id:
                for ws in sockets:
                    await ws.send_json(status_msg.model_dump())

    except Exception as e:
        print("MSG_STATUS ERROR:", e)



# PRESENCE (ONLINE / OFFLINE MANUAL SIGNAL)
async def handle_presence(user_id: int, payload: PresencePayload):
    try:
        status = payload.status

        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))
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
            Message.fld_client_message_id == message_id,
            Message.fld_sender_id == user_id
        ).first()

        if not message:
            return
        # Verify participant involvement in the conversation
        if not await verify_participant(user_id, message.fld_conversation_id, db):
            return

        # Construction server timestamp
        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))

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
        message.fld_is_edited = True

        # Re-embed edited message so search stays accurate
        try:
            message.fld_embedding = embed_text(new_text)
        except Exception as emb_err:
            print(f"[Embedding] Re-embed failed (non-fatal): {emb_err}")

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
                editedAt=format_datetime_to_zulu(edited_at) if edited_at else server_timestamp,
                isEdited=True
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
        import traceback
        traceback.print_exc()
        print("EDIT_MSG ERROR:", e)



# DELETE MULTIPLE MESSAGES
async def handle_delete_messages(user_id: int, payload: DeleteMultipleMessagesPayload, db: Session):
    try:
        server_timestamp = format_datetime_to_zulu(datetime.now(timezone.utc))
        ack_items = []
        broadcast_by_conv = {}

        for msg_item in payload.messages:
            message_id = msg_item.id
            delete_type = msg_item.deleteType
            deleted_at_for_everyone = msg_item.deletedForEveryoneAt
            deleted_at_for_me = msg_item.deletedForMeAt

            message = db.query(Message).filter(
                Message.fld_client_message_id == message_id
            ).first()

            # Verify participant involvement
            if message and not await verify_participant(user_id, message.fld_conversation_id, db):
                # Append error for permission denied due to not participant
                ack_items.append(
                    AckDeleteMultipleMessagesItem(
                        id=str(message_id),
                        deleteType=delete_type,
                        deletedForEveryoneAt=deleted_at_for_everyone,
                        deletedForMeAt=deleted_at_for_me,
                        error="PERMISSION_DENIED"
                    )
                )
                continue

            if not message:
                ack_items.append(
                    AckDeleteMultipleMessagesItem(
                        id=str(message_id),
                        deleteType=delete_type,
                        deletedForEveryoneAt=deleted_at_for_everyone,
                        deletedForMeAt=deleted_at_for_me,
                        error="INVALID_ID"
                    )
                )
                continue

            # Authorization Check
            if delete_type in ("deleteForEveryone", "both"):
                if message.fld_sender_id != user_id:
                    ack_items.append(
                        AckDeleteMultipleMessagesItem(
                            id=str(message_id),
                            deleteType=delete_type,
                            deletedForEveryoneAt=deleted_at_for_everyone,
                            deletedForMeAt=deleted_at_for_me,
                            error="PERMISSION_DENIED"
                        )
                    )
                    continue

            # Process Deletion logic
            try:
                if delete_type == "deleteForEveryone":
                    message.fld_is_deleted_for_everyone = True
                    message.fld_deleted_for_everyone_at = deleted_at_for_everyone or server_timestamp
                    db.commit()
                elif delete_type == "deleteForMe":
                    new_delete = MessageDelete(
                        fld_message_id=message.fld_message_id,
                        fld_user_id=user_id,
                        fld_deleted_at=deleted_at_for_me or server_timestamp
                    )
                    db.add(new_delete)
                    db.commit()
                elif delete_type == "both":
                    message.fld_is_deleted_for_everyone = True
                    message.fld_deleted_for_everyone_at = deleted_at_for_everyone or server_timestamp
                    new_delete = MessageDelete(
                        fld_message_id=message.fld_message_id,
                        fld_user_id=user_id,
                        fld_deleted_at=deleted_at_for_me or server_timestamp
                    )
                    db.add(new_delete)
                    db.commit()

                # Add to ack payload
                ack_items.append(
                    AckDeleteMultipleMessagesItem(
                        id=str(message_id),
                        deleteType=delete_type,
                        deletedForEveryoneAt=deleted_at_for_everyone or server_timestamp if delete_type in ("deleteForEveryone", "both") else None,
                        deletedForMeAt=deleted_at_for_me or server_timestamp if delete_type in ("deleteForMe", "both") else None
                    )
                )

                # Collect broadcast items
                if delete_type in ("deleteForEveryone", "both"):
                    conv_id = message.fld_conversation_id
                    if conv_id not in broadcast_by_conv:
                        broadcast_by_conv[conv_id] = []
                    
                    broadcast_by_conv[conv_id].append(
                        ReceiveDeleteMultipleMessagesItem(
                            id=str(message_id),
                            deleteType=delete_type,
                            deletedForEveryoneAt=deleted_at_for_everyone or server_timestamp
                        )
                    )

            except Exception as item_err:
                db.rollback()
                ack_items.append(
                    AckDeleteMultipleMessagesItem(
                        id=str(message_id),
                        deleteType=delete_type,
                        deletedForEveryoneAt=deleted_at_for_everyone,
                        deletedForMeAt=deleted_at_for_me,
                        error=f"ERROR: {str(item_err)}"
                    )
                )

        # Send ACK back to the sender
        ack_payload = AckDeleteMultipleMessagesPayload(
            protocolVersion=payload.protocolVersion,
            messages=ack_items
        )
        ack_msg = WsServerMessage(
            event="ACK_DELETE_MSGS",
            payload=ack_payload,
            timestamp=server_timestamp
        )
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json(ack_msg.model_dump())

        # Broadcast RECEIVE_DELETE_MSGS per conversation
        for conv_id, items in broadcast_by_conv.items():
            if not items:
                continue

            broadcast_payload = ReceiveDeleteMultipleMessagesPayload(
                protocolVersion=payload.protocolVersion,
                messages=items
            )
            receive_msg = WsServerMessage(
                event="RECEIVE_DELETE_MSGS",
                payload=broadcast_payload,
                timestamp=server_timestamp
            )

            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.fld_conversation_id == conv_id
            ).all()
            unique_participant_ids = {p.fld_user_id for p in participants}

            for target_uid in unique_participant_ids:
                if target_uid == user_id:
                    continue
                target_sockets = manager.active_connections.get(target_uid, [])
                for ws in target_sockets:
                    await ws.send_json(receive_msg.model_dump())

    except Exception as e:
        print("DELETE_MSGS ERROR:", e)