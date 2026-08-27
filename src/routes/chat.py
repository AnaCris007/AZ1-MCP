from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends

from az1_api.dependencies import get_chat_answerer
from schemas.chat import ChatErrorCode, ChatRequest, ChatResponse
from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    AnswerChatMessage,
    ChatReceptionError,
    ChatReceptionErrorCode,
)

router = APIRouter(tags=["chat"])


class ChatAPIError(Exception):
    def __init__(self, status_code: int, error: ChatErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    status_code: int
    error: ChatErrorCode
    message: str


_ERROR_DETAILS = {
    ChatReceptionErrorCode.EMPTY_MESSAGE: _HTTPErrorDetails(
        422,
        "empty_message",
        "A mensagem não pode estar vazia.",
    ),
    ChatReceptionErrorCode.MESSAGE_TOO_LONG: _HTTPErrorDetails(
        422,
        "message_too_long",
        f"A mensagem excede o limite de {MAX_MESSAGE_LENGTH} caracteres.",
    ),
}


@router.post("/chat", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    answerer: AnswerChatMessage = Depends(get_chat_answerer),
) -> ChatResponse:
    try:
        reply = answerer.answer(payload.message)
    except ChatReceptionError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise ChatAPIError(details.status_code, details.error, details.message) from exc

    return ChatResponse(reply=reply.text)
