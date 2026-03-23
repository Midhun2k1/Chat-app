from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.db.database import sessionLocal
from app.db.models import Message
from datetime import datetime

router = APIRouter()

active_connections = {}  # user_id -> websocket


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()

    active_connections[user_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()

            receiver_id = data.get("receiver_id")
            message = data.get("message")

            #SAVE TO DB
            db = sessionLocal()

            new_msg = Message(
                fld_sender_id=user_id,
                fld_receiver_id=receiver_id,
                fld_message=message,
                fld_created_at=datetime.utcnow()
            )

            db.add(new_msg)
            db.commit()
            db.close()

            # SEND REAL-TIME
            if receiver_id in active_connections:
                await active_connections[receiver_id].send_json({
                    "from": user_id,
                    "message": message
                })

    except WebSocketDisconnect:
        active_connections.pop(user_id, None)