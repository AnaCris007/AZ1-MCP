from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, Depends

from az1_api.dependencies import get_chat_answerer, get_gravador_auditoria
from schemas.chat import ChatErrorCode, ChatRequest, ChatResponse
from services.auditoria_service import GravarConsulta
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
    background_tasks: BackgroundTasks,
    answerer: AnswerChatMessage = Depends(get_chat_answerer),
    gravador: GravarConsulta = Depends(get_gravador_auditoria),
) -> ChatResponse:
    inicio = time.monotonic()
    resposta_texto: str | None = None
    try:
        reply = answerer.answer(payload.message, payload.conversation_id)
        resposta_texto = reply.text
    except ChatReceptionError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise ChatAPIError(details.status_code, details.error, details.message) from exc
    finally:
        duracao_ms = int((time.monotonic() - inicio) * 1000)
        # Nota: se ChatAPIError for lançado, o exception handler cria uma nova
        # JSONResponse sem background tasks — requisições inválidas (422) não
        # são auditadas. Comportamento intencional para M7.
        background_tasks.add_task(
            gravador.gravar,
            mensagem=payload.message,
            resposta=resposta_texto,
            conversation_id=payload.conversation_id,
            duracao_ms=duracao_ms,
        )

    return ChatResponse(reply=reply.text)
