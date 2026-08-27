from typing import Literal

from pydantic import BaseModel

ChatErrorCode = Literal[
    "bad_request",
    "empty_message",
    "message_too_long",
    "internal_error",
]


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class ChatResponse(BaseModel):
    reply: str
