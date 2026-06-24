from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from app.websocket.manager import manager
from app.websocket.handlers import (
    handle_send_message,
    handle_typing,
    handle_message_status,
    handle_presence,
    handle_edit_message,
    handle_delete_messages
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
            try:
                data = await websocket.receive_json()
                ws_msg = WsClientMessage(**data)
                payload = ws_msg.payload
            except WebSocketDisconnect:
                # Propagate disconnect to outer handler
                raise
            except Exception as e:
                print(f"WS Wrapper Validation Error: {e}", flush=True)
                continue

            from app.schemas.websocket import (
                SendMessagePayload, TypingPayload, MessageStatusPayload,
                PresencePayload, EditMessagePayload,
                DeleteMultipleMessagesPayload,
            )

            try:
                if isinstance(payload, SendMessagePayload):
                    await handle_send_message(user_id, payload, db)
                elif isinstance(payload, TypingPayload):
                    await handle_typing(user_id, payload, db)
                elif isinstance(payload, MessageStatusPayload):
                    await handle_message_status(user_id, payload, db)
                elif isinstance(payload, PresencePayload):
                    await handle_presence(user_id, payload)
                elif isinstance(payload, EditMessagePayload):
                    await handle_edit_message(user_id, payload, db)
                elif isinstance(payload, DeleteMultipleMessagesPayload):
                    await handle_delete_messages(user_id, payload, db)
            except Exception as handler_err:
                print(f"Handler error: {handler_err}", flush=True)
                continue

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        await websocket.close()
        await manager.broadcast_online_users()
    except Exception as e:
        print(f"Unexpected WS error: {e}", flush=True)
        manager.disconnect(user_id, websocket)
        await websocket.close()
        await manager.broadcast_online_users()
    finally:
        db.close()