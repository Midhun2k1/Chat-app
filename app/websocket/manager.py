from fastapi import WebSocket
from typing import Dict, List
from datetime import datetime, timezone
from app.utils.time_utils import format_datetime_to_zulu
from app.db.database import SessionLocal
from app.db.models import ConversationParticipant


class ConnectionManager:
    def __init__(self):
        # user_id -> list of sockets (multi-tab support)
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # remove user if no sockets left
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_users(self, user_ids: List[int], message: dict):
        for user_id in user_ids:
            await self.send_personal_message(user_id, message)

    async def broadcast_online_users(self):
        # Obtain a DB session to query conversation participants
        db = SessionLocal()
        try:
            online_user_ids = list(self.active_connections.keys())
            if not online_user_ids:
                return

            # Fetch all participant rows for online users
            participant_rows = (
                db.query(ConversationParticipant)
                .filter(ConversationParticipant.fld_user_id.in_(online_user_ids))
                .all()
            )

            # Map conversation_id -> set of online user ids in that conversation
            conv_to_user_ids: dict[int, set[int]] = {}
            user_to_convs: dict[int, set[int]] = {uid: set() for uid in online_user_ids}
            for row in participant_rows:
                conv_id = row.fld_conversation_id
                uid = row.fld_user_id
                conv_to_user_ids.setdefault(conv_id, set()).add(uid)
                user_to_convs[uid].add(conv_id)

            # For each online user, compute payload of online users sharing a conversation
            for user_id in online_user_ids:
                visible_user_ids: set[int] = set()
                for conv_id in user_to_convs.get(user_id, []):
                    visible_user_ids.update(conv_to_user_ids.get(conv_id, set()))
                # Include the user themselves for completeness
                visible_user_ids.add(user_id)
                message = {
                    "event": "ONLINE_USERS",
                    "payload": {
                        "user_ids": list(visible_user_ids),
                        "message": "Online users update"
                    },
                    "timestamp": format_datetime_to_zulu(datetime.now(timezone.utc)),
                }
                await self.send_personal_message(user_id, message)
        finally:
            db.close()

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.active_connections


# global instance
manager = ConnectionManager()