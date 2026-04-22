from datetime import datetime
from sqlalchemy.orm import Session
from app.websocket.manager import manager
from app.db.models import Message, ConversationParticipant, MessageDelete



# SEND MESSAGE
async def handle_send_message(user_id: int, payload: dict, db: Session):
    try:
        conversation_id = payload.get("chatId")
        text = payload.get("text")
        client_msg_id = payload.get("id")

        if not conversation_id or not text:
            return

        # Save message in DB
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

        server_timestamp = int(datetime.utcnow().timestamp())

        # ACK to sender (important for optimistic UI)
        """ sender_ws = manager.active_connections.get(user_id)
        if sender_ws:
            await sender_ws.send_json({
                "type": "ACK_SEND_MSG",
                "payload": {
                    "id": client_msg_id,
                    "serverTimestamp": server_timestamp
                }
            }) """
        
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json({
                "type": "ACK_SEND_MSG",
                "payload": {
                    "id": client_msg_id,
                    "serverTimestamp": server_timestamp
                }
            })

        # Get participants
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.fld_conversation_id == conversation_id
        ).all()

        # Broadcast message
        for p in participants:
            # Skip sending the message back to the sender since they already got the ACK
            if p.fld_user_id == user_id:
                continue

            target_sockets = manager.active_connections.get(p.fld_user_id, [])

            for ws in target_sockets:
                await ws.send_json({
                    "type": "RECEIVE_MSG",
                    "payload": {
                        "id": client_msg_id,
                        "chatId": str(conversation_id),
                        "text": text,
                        "senderId": str(user_id),
                        "createdAt": new_message.fld_created_at.isoformat(),
                        "serverTimestamp": server_timestamp
                    }
                })

    except Exception as e:
        print("SEND_MSG ERROR:", e)



# TYPING INDICATOR
async def handle_typing(user_id: int, payload: dict):
    try:
        chat_id = payload.get("chatId")
        is_typing = payload.get("isTyping")

        if chat_id is None:
            return

        # broadcast to others
        """ for uid, ws in manager.active_connections.items():
            if uid != user_id:
                await ws.send_json({
                    "type": "TYPING",
                    "payload": {
                        "chatId": str(chat_id),
                        "userId": str(user_id),
                        "isTyping": is_typing
                    }
                }) """
        
        for uid, sockets in manager.active_connections.items():
            if uid != user_id:
                for ws in sockets:
                    await ws.send_json({
                        "type": "TYPING",
                        "payload": {
                            "chatId": str(chat_id),
                            "userId": str(user_id),
                            "isTyping": is_typing
                        }
                    })

    except Exception as e:
        print("TYPING ERROR:", e)


# =========================================================
# MESSAGE STATUS (DELIVERED / READ)
# =========================================================
async def handle_message_status(user_id: int, payload: dict, db: Session):
    try:
        message_id = payload.get("messageId")
        status = payload.get("status")

        if not message_id or not status:
            return

        # Update DB for read
        if status == "read":
            db.query(Message).filter(
                Message.client_msg_id == message_id
            ).update({
                "fld_is_read": True
            })
            db.commit()

        # Broadcast status to all connected users
        """ for ws in manager.active_connections.values():
            await ws.send_json({
                "type": "MSG_STATUS",
                "payload": {
                    "messageId": str(message_id),
                    "status": status
                }
            }) """
        for sockets in manager.active_connections.values():
            for ws in sockets:
                await ws.send_json({
                "type": "MSG_STATUS",
                "payload": {
                    "messageId": str(message_id),
                    "status": status
                }
            })

    except Exception as e:
        print("MSG_STATUS ERROR:", e)



# PRESENCE (ONLINE / OFFLINE MANUAL SIGNAL)
async def handle_presence(user_id: int, payload: dict):
    try:
        status = payload.get("status")

        if status not in ["online", "offline"]:
            return

        for uid, sockets in manager.active_connections.items():
            if uid != user_id:
                for ws in sockets:
                    await ws.send_json({
                        "type": "PRESENCE",
                        "payload": {
                            "userId": str(user_id),
                            "status": status
                        }
                    })

    except Exception as e:
        print("PRESENCE ERROR:", e)



# EDIT MESSAGE
async def handle_edit_message(user_id: int, payload: dict, db: Session):
    try:
        message_id = payload.get("id")
        new_text = payload.get("text")
        edited_at = payload.get("editedAt")

        if not message_id or not new_text:
            return

        message = db.query(Message).filter(
            Message.client_msg_id == message_id,
            Message.fld_sender_id == user_id
        ).first()

        if not message:
            return

        # Only sender can edit
        if message.fld_sender_id != user_id:
            return

        message.fld_message = new_text
        db.commit()

        # ACK sender
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json({
                "type": "ACK_EDIT_MSG",
                "payload": {
                    "id": str(message_id),
                    "editedAt": int(datetime.utcnow().timestamp())
                }
            })

        # Broadcast edit
        for sockets in manager.active_connections.values():
            for ws in sockets:
                await ws.send_json({
                    "type": "RECEIVE_EDIT_MSG",
                    "payload": {
                        "id": str(message_id),
                        "text": new_text,
                        "editedAt": edited_at
                    }
                })

    except Exception as e:
        print("EDIT_MSG ERROR:", e)



# DELETE MESSAGE
async def handle_delete_message(user_id: int, payload: dict, db: Session):
    try:
        message_id = payload.get("id")
        delete_type = payload.get("deleteType")
        deleted_at = payload.get("deletedAt")

        if not message_id or not delete_type:
            return

        message = db.query(Message).filter(
            Message.client_msg_id == message_id
        ).first()

        if not message:
            return

        if delete_type == "deleteForEveryone":
            if message.fld_sender_id != user_id:
                return
            
            message.fld_is_deleted_for_everyone = True
            #message.fld_message = "This message was deleted"
            db.commit()

        elif delete_type == "deleteForMe":
            new_delete = MessageDelete(
                message_id=message_id,
                user_id=user_id
            )
            db.add(new_delete)

        # ACK sender
        sender_sockets = manager.active_connections.get(user_id, [])
        for ws in sender_sockets:
            await ws.send_json({
                "type": "ACK_DELETE_MSG",
                "payload": {
                    "id": str(message_id),
                    "deletedAt": int(datetime.utcnow().timestamp())
                }
            })

        # Broadcast delete
        for sockets in manager.active_connections.values():
            for ws in sockets:
                await ws.send_json({
                    "type": "RECEIVE_DELETE_MSG",
                    "payload": {
                        "id": str(message_id),
                        "deleteType": delete_type,
                        "deletedAt": deleted_at
                    }
                })

    except Exception as e:
        print("DELETE_MSG ERROR:", e)