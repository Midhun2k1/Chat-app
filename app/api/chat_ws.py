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


