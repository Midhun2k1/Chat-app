from pydantic import BaseModel
from typing import Literal, Optional, Any, Union, List

# --- Incoming Payloads (Client -> Server) ---

class SendMessagePayload(BaseModel):
    chatId: int
    text: str
    id: Union[int, str]  # client_message_id

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

class DeleteMessagePayload(BaseModel):
    id: Union[int, str]
    deleteType: Literal["deleteForMe", "deleteForEveryone", "both"]
    deletedForEveryoneAt: Optional[Union[int, str]] = None
    deletedForMeAt: Optional[Union[int, str]] = None

# --- Incoming Message Wrapper ---

class WsClientMessage(BaseModel):
    event: Literal["SEND_MSG", "TYPING", "MSG_STATUS", "PRESENCE", "EDIT_MSG", "DELETE_MSG"]
    payload: Union[
        SendMessagePayload,
        TypingPayload,
        MessageStatusPayload,
        PresencePayload,
        EditMessagePayload,
        DeleteMessagePayload
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

class AckDeleteMessagePayload(BaseModel):
    id: str
    deleteType: Literal["deleteForMe", "deleteForEveryone", "both"]

class ReceiveDeleteMessagePayload(BaseModel):
    id: str
    deleteType: Literal["deleteForEveryone", "both"] # deleteForMe is not broadcast

class ErrorPayload(BaseModel):
    message: str

# --- Outgoing Message Wrapper ---

class WsServerMessage(BaseModel):
    event: Literal[
        "ACK_SEND_MSG", 
        "RECEIVE_MSG", 
        "TYPING", 
        "MSG_STATUS", 
        "PRESENCE", 
        "ACK_EDIT_MSG", 
        "RECEIVE_EDIT_MSG", 
        "ACK_DELETE_MSG", 
        "RECEIVE_DELETE_MSG", 
        "ERROR"
    ]
    payload: Union[
        AckSendMessagePayload,
        ReceiveMessagePayload,
        TypingBroadcastPayload,
        MessageStatusBroadcastPayload,
        PresenceBroadcastPayload,
        AckEditMessagePayload,
        ReceiveEditMessagePayload,
        AckDeleteMessagePayload,
        ReceiveDeleteMessagePayload,
        ErrorPayload
    ]
    timestamp: str