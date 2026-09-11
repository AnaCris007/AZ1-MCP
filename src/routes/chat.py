from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, Depends

from az1_api.dependencies import get_chat_answerer, get_gravador_auditoria
from rag.retriever import ResultadoBusca
from schemas.chat import ChatErrorCode, ChatRequest, ChatResponse, FonteCitada
from services.auditoria_service import GravarConsulta
from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    AnswerChatMessage,
    ChatReceptionError,
    ChatReceptionErrorCode,
)

router = APIRouter(tags=["chat"])

# Captura tanto `[3]` quanto `[3, 4]`.
_CITACAO = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

# O mesmo, com o espaço que vem antes — para que "crítico [3, 4]." vire
# "crítico." e não "crítico ."
_CITACAO_COM_ESPACO = re.compile(r"[ \t]*\[\d+(?:\s*,\s*\d+)*\]")


def limpar_citacoes(texto: str) -> str:
    """Tira os `[3, 4]` do texto exibido, preservando a lista de fontes.

    O modelo CONTINUA sendo instruído a citar, e isso não é contradição: a
    citação é como ele informa quais trechos sustentaram a resposta. É ela que
    permite a `fontes_citadas` devolver os dois que foram usados em vez dos
    cinco que foram recuperados.

    Ou seja, o número é sinal de trabalho interno, não de interface. Removê-lo
    aqui, e só aqui, mantém o sinal e tira o ruído.
    """
    return re.sub(r" {2,}", " ", _CITACAO_COM_ESPACO.sub("", texto)).strip()


def fontes_citadas(texto: str, recuperadas: Sequence[ResultadoBusca]) -> list[FonteCitada]:
    """Só as fontes que a resposta de fato citou.

    A busca entrega cinco trechos ao modelo, e ele costuma usar dois. Listar os
    cinco como "fontes" seria ruído: o usuário abriria um documento que não
    sustenta afirmação nenhuma, e a lista deixaria de significar algo.

    A numeração ORIGINAL é preservada. Renumerar quebraria a ligação com o `[3]`
    escrito no texto, que é justamente o que torna a citação conferível.
    """
    numeros = {
        int(n)
        for grupo in _CITACAO.findall(texto)
        for n in grupo.split(",")
        if n.strip().isdigit()
    }
    return [
        FonteCitada(
            posicao=n,
            projeto_id=fonte.projeto_id,
            tipo_documento=fonte.tipo_documento,
            arquivo_origem=fonte.arquivo_origem,
            secao=fonte.secao,
            score=fonte.score,
            chunk_id=fonte.chunk_id,
            trecho=fonte.texto,
        )
        for n, fonte in enumerate(recuperadas, start=1)
        if n in numeros
    ]


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
    ChatReceptionErrorCode.SERVICE_UNAVAILABLE: _HTTPErrorDetails(
        503,
        "service_unavailable",
        "O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.",
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
    fontes: list[FonteCitada] = []
    try:
        reply = answerer.answer(payload.message, payload.conversation_id)
        # A ordem importa: as fontes saem do texto AINDA com os marcadores, e só
        # depois o texto é limpo. Invertido, não haveria como saber quais
        # trechos o modelo usou.
        fontes = fontes_citadas(reply.text, reply.fontes)
        resposta_texto = limpar_citacoes(reply.text)
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

    # `resposta_texto` é o mesmo que foi para a auditoria: o que a pessoa viu é
    # o que fica registrado. A ligação afirmação↔fonte não se perde, porque ela
    # vive em `mensagem_fonte.posicao`.
    return ChatResponse(reply=resposta_texto, fontes=fontes)
