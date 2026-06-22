from pydantic import BaseModel
from typing import Literal, Optional, Any, Union, List

# --- Incoming Payloads (Client -> Server) ---

class SendMessagePayload(BaseModel):
    chatId: int
    text: str
    id: Union[int, str]  # client_message_id
    replyTo: Optional[str] = None
    createdAt: Optional[Union[int, float, str]] = None
    type: Optional[str] = "text"
    audioUrl: Optional[str] = None
    durationSeconds: Optional[int] = None



class TypingPayload(BaseModel):
    chatId: int
    isTyping: bool

class MessageStatusPayload(BaseModel):
    messageId: Union[int, str]
    status: Literal["read", "delivered"]

class PresencePayload(BaseModel):
    status: Literal["online", "offline"]

class EditMessagePayload(BaseModel):
    id: Union[int, str]
    text: str
    editedAt: Optional[Union[int, str]] = None

class DeleteMultipleMessagesItem(BaseModel):
    id: Union[int, str]
    deleteType: Literal["deleteForMe", "deleteForEveryone", "both"]
    deletedForEveryoneAt: Optional[Union[int, str]] = None
    deletedForMeAt: Optional[Union[int, str]] = None

class DeleteMultipleMessagesPayload(BaseModel):
    protocolVersion: str = "1.0"
    messages: List[DeleteMultipleMessagesItem]

# --- Incoming Message Wrapper ---

class WsClientMessage(BaseModel):
    event: Literal["SEND_MSG", "TYPING", "MSG_STATUS", "PRESENCE", "EDIT_MSG", "DELETE_MSGS"]
    payload: Union[
        SendMessagePayload,
        TypingPayload,
        MessageStatusPayload,
        PresencePayload,
        EditMessagePayload,
        DeleteMultipleMessagesPayload
    ]
    timestamp: Optional[Union[int, str]] = None

# --- Outgoing Payloads (Server -> Client) ---

class AckSendMessagePayload(BaseModel):
    id: str
    serverTimestamp: str

class ReceiveMessagePayload(BaseModel):
    id: str
    chatId: str
    text: str
    senderId: str
    createdAt: str
    serverTimestamp: str
    isDeletedForEveryone: bool
    isEdited: bool = False
    replyTo: Optional[str] = None
    isBot: Optional[bool] = False
    type: Optional[str] = "text"
    audioUrl: Optional[str] = None
    durationSeconds: Optional[int] = None



class TypingBroadcastPayload(BaseModel):
    chatId: str
    userId: str
    isTyping: bool

class MessageStatusBroadcastPayload(BaseModel):
    messageId: str
    status: str

class PresenceBroadcastPayload(BaseModel):
    userId: str
    status: str

class AckEditMessagePayload(BaseModel):
    id: str
    editedAt: str

class ReceiveEditMessagePayload(BaseModel):
    id: str
    text: str
    editedAt: Optional[str] = None
    isEdited: bool = True

class AckDeleteMultipleMessagesItem(BaseModel):
    id: str
    deleteType: Literal["deleteForMe", "deleteForEveryone", "both"]
    deletedForEveryoneAt: Optional[str] = None
    deletedForMeAt: Optional[str] = None
    error: Optional[str] = None

class AckDeleteMultipleMessagesPayload(BaseModel):
    protocolVersion: str = "1.0"
    messages: List[AckDeleteMultipleMessagesItem]

class ReceiveDeleteMultipleMessagesItem(BaseModel):
    id: str
    deleteType: Literal["deleteForEveryone", "both"]
    deletedForEveryoneAt: str

class ReceiveDeleteMultipleMessagesPayload(BaseModel):
    protocolVersion: str = "1.0"
    messages: List[ReceiveDeleteMultipleMessagesItem]

class ErrorPayload(BaseModel):
    message: str

class OnlineUsersPayload(BaseModel):
    user_ids: List[int]  # list of online user IDs visible to the recipient
    message: str


class WsServerMessage(BaseModel):
    event: Literal[
        "ACK_SEND_MSG", 
        "RECEIVE_MSG", 
        "TYPING", 
        "MSG_STATUS", 
        "PRESENCE", 
        "ACK_EDIT_MSG", 
        "RECEIVE_EDIT_MSG", 
        "ACK_DELETE_MSGS",
        "RECEIVE_DELETE_MSGS",
        "ERROR",
        "ONLINE_USERS"
    ]
    payload: Union[
        AckSendMessagePayload,
        ReceiveMessagePayload,
        TypingBroadcastPayload,
        MessageStatusBroadcastPayload,
        PresenceBroadcastPayload,
        AckEditMessagePayload,
        ReceiveEditMessagePayload,
        AckDeleteMultipleMessagesPayload,
        ReceiveDeleteMultipleMessagesPayload,
        ErrorPayload,
        OnlineUsersPayload
    ]
    timestamp: str