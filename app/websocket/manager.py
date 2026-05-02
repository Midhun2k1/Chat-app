from fastapi import WebSocket
from typing import Dict, List
from datetime import datetime


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
        online_users = list(self.active_connections.keys())

        message = {
            "event": "ONLINE_USERS",
            "payload": online_users,
            "timestamp": int(datetime.utcnow().timestamp())
        }

        # send to all users
        for user_id in self.active_connections:
            await self.send_personal_message(user_id, message)

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.active_connections


# global instance
manager = ConnectionManager()