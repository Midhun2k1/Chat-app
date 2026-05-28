from pydantic import BaseModel
from typing import List, Optional

class ParentMessageItem(BaseModel):
    message_id: str
    sender_id: int
    message: str

class MessageItem(BaseModel):
    message_id: str
    sender_id: int
    message: str
    created_at: str
    is_read: bool
    is_deleted_for_everyone: bool
    is_delete_for_me: bool
    reply_to: Optional[ParentMessageItem] = None


class MessageList(BaseModel):
    messages: List[MessageItem]

class MessageFetchRequest(BaseModel):
    conversation_id: int
    skip: Optional[int] = 0
    limit: Optional[int] = 50

class MarkAsReadRequest(BaseModel):
    conversation_id: int
 