from pydantic import BaseModel
from typing import Optional

class PingyDetails(BaseModel):
    username: str
    chatId: str
    avatarUrl: str
    pingyUserId: str
    isEnabled: bool

class PingyDetailsResponse(BaseModel):
    pingyDetails: PingyDetails
    conversationId: Optional[int] = None
