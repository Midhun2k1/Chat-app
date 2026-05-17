from pydantic import BaseModel
from typing import List, Optional

class ConversationID(BaseModel):
    conversation_id: int

class ChatParticipants(BaseModel):
    userIDs: List[str]

class ChatItem(BaseModel):
    id: str
    name: str
    type: str  # 'individual' or 'group'
    unread_count: int
    last_message_text: Optional[str] = None
    updated_at: str  # ISO Zulu time string
    avatar_url: Optional[str] = None
    participants: ChatParticipants
    lastMessageSentUsername: str

class ChatList(BaseModel):
    chats: List[ChatItem]

class ConversationCreateRequest(BaseModel):
    user_id: int

class ChatUserDetailsRequest(BaseModel):
    chatId: str

class UserDetail(BaseModel):
    userId: str
    name: str
    is_me: bool
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None

