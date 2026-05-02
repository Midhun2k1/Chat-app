from pydantic import BaseModel
from typing import List

class ConversationID(BaseModel):
    conversation_id: int

class ChatItem(BaseModel):
    conversation_id: int
    user_id: int
    username: str
    last_message: str
    timestamp: str
    unread_count: int

class ChatList(BaseModel):
    chats: List[ChatItem]

class ConversationCreateRequest(BaseModel):
    user_id: int