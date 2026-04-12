from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from app.websocket.manager import manager
from app.websocket.handlers import (
    handle_send_message,
    handle_typing,
    handle_message_status,
    handle_presence,
    handle_edit_message,
    handle_delete_message
)
from app.db.database import SessionLocal
from app.auth.auth import SECRET_KEY, ALGORITHM

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            await websocket.close(code=1008)
            return

    except JWTError:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    await manager.broadcast_online_users()

    db = SessionLocal()

    try:
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            payload = data.get("payload")

            if msg_type == "SEND_MSG":
                await handle_send_message(user_id, payload, db)

            elif msg_type == "TYPING":
                await handle_typing(user_id, payload)

            elif msg_type == "MSG_STATUS":
                await handle_message_status(user_id, payload, db)

            elif msg_type == "PRESENCE":
                await handle_presence(user_id, payload)

            elif msg_type == "EDIT_MSG":
                await handle_edit_message(user_id, payload, db)

            elif msg_type == "DELETE_MSG":
                await handle_delete_message(user_id, payload, db)

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)  # ✅ FIXED
        await manager.broadcast_online_users()


    finally:
        db.close()























""" from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Message, ConversationParticipant
from app.auth.auth import SECRET_KEY, ALGORITHM

router = APIRouter()
active_connections = {}  # {user_id: websocket}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            await websocket.close(code=1008)
            return

    except JWTError:
        await websocket.close(code=1008)
        return

    #Store connection
    active_connections[user_id] = websocket
    print(f"✅ User {user_id} connected")

    db: Session = SessionLocal()

    try:
        while True:
            print("👂 Waiting for message...")

            data = await websocket.receive_json()
            print("📩 Received:", data)

            conversation_id = data.get("conversation_id")
            message_text = data.get("message")

            # Validate input
            if not conversation_id or not message_text:
                await websocket.send_json({"error": "Invalid payload"})
                continue

            #Check if user belongs to conversation
            participant = db.query(ConversationParticipant).filter(
                ConversationParticipant.fld_conversation_id == conversation_id,
                ConversationParticipant.fld_user_id == user_id
            ).first()

            if not participant:
                await websocket.send_json({"error": "Not part of conversation"})
                continue

            #Save message
            new_message = Message(
                fld_conversation_id=conversation_id,
                fld_sender_id=user_id,
                fld_message=message_text
            )

            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            print(f"➡ Message saved in conversation {conversation_id}")

            #Get all participants of this conversation
            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.fld_conversation_id == conversation_id
            ).all()

            #Send message to all connected participants
            for p in participants:
                target_user_id = p.fld_user_id

                if target_user_id in active_connections:
                    await active_connections[target_user_id].send_json({
                        "conversation_id": conversation_id,
                        "from": user_id,
                        "message": message_text,
                        "timestamp": str(new_message.fld_created_at)
                    })

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")

    except Exception as e:
        print("ERROR:", e)

    finally:

        active_connections.pop(user_id, None)
        db.close() """