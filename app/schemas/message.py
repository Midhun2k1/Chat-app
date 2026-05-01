from pydantic import BaseModel
from typing import List

class MessageItem(BaseModel):
    message_id: int
    sender_id: int
    message: str
    created_at: str
    is_read: bool

class MessageList(BaseModel):
    messages: List[MessageItem]
