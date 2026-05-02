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
from app.schemas.websocket import WsClientMessage

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        try:
            user_id = int(payload.get("user_id"))
        except (ValueError, TypeError):
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
            # print(f"DEBUG: Incoming WS data from user {user_id}: {data}") # Uncomment for deep debugging

            try:
                ws_msg = WsClientMessage(**data)
                msg_type = ws_msg.type
                raw_payload = ws_msg.payload
            except Exception as e:
                print(f"WS Wrapper Validation Error: {e}")
                continue

            from app.schemas.websocket import (
                SendMessagePayload, TypingPayload, MessageStatusPayload, 
                PresencePayload, EditMessagePayload, DeleteMessagePayload
            )

            if msg_type == "SEND_MSG":
                try:
                    payload = SendMessagePayload(**raw_payload)
                    await handle_send_message(user_id, payload, db)
                except Exception as e:
                    print(f"SEND_MSG Payload Error: {e}")

            elif msg_type == "TYPING":
                try:
                    payload = TypingPayload(**raw_payload)
                    await handle_typing(user_id, payload)
                except Exception as e:
                    print(f"TYPING Payload Error: {e}")

            elif msg_type == "MSG_STATUS":
                try:
                    payload = MessageStatusPayload(**raw_payload)
                    await handle_message_status(user_id, payload, db)
                except Exception as e:
                    print(f"MSG_STATUS Payload Error: {e}")

            elif msg_type == "PRESENCE":
                try:
                    payload = PresencePayload(**raw_payload)
                    await handle_presence(user_id, payload)
                except Exception as e:
                    print(f"PRESENCE Payload Error: {e}")

            elif msg_type == "EDIT_MSG":
                try:
                    payload = EditMessagePayload(**raw_payload)
                    await handle_edit_message(user_id, payload, db)
                except Exception as e:
                    print(f"EDIT_MSG Payload Error: {e}")

            elif msg_type == "DELETE_MSG":
                try:
                    payload = DeleteMessagePayload(**raw_payload)
                    await handle_delete_message(user_id, payload, db)
                except Exception as e:
                    print(f"DELETE_MSG Payload Error: {e}")

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)  # ✅ FIXED
        await manager.broadcast_online_users()


    finally:
        db.close()


 