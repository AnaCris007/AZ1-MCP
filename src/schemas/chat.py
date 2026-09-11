from typing import Literal

from pydantic import BaseModel

ChatErrorCode = Literal[
    "bad_request",
    "empty_message",
    "message_too_long",
    "service_unavailable",
    "internal_error",
]


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class FonteCitada(BaseModel):
    """Uma fonte que fundamentou a resposta.

    `posicao` é o número que a resposta cita entre colchetes, e é o mesmo
    inteiro que `auditoria.mensagem_fonte.posicao` grava. Um número só, nos três
    lugares — é o que torna a citação conferível em vez de decorativa.
    """

    posicao: int
    arquivo_origem: str
    secao: str = ""
    score: float
    chunk_id: str = ""
    trecho: str = ""


class ChatResponse(BaseModel):
    reply: str
    # Vazia quando a resposta não se apoiou em documento nenhum — inclusive nas
    # respostas padrão de "não encontrei". O frontend pode usar isso para não
    # renderizar o bloco de fontes.
    fontes: list[FonteCitada] = []
