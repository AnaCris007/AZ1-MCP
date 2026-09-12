from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, Depends

from az1_api.dependencies import (
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    require_authenticated_user,
)
from rag.retriever import ResultadoBusca
from schemas.chat import ChatErrorCode, ChatRequest, ChatResponse, FonteCitada
from services.auth_service import AuthenticatedUser
from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    AnswerChatMessage,
    ChatReceptionError,
    ChatReceptionErrorCode,
    ChatReply,
)
from services.conversa_repository import (
    ConversaNaoGravada,
    ConversaRepository,
    FonteDaResposta,
    PersistenciaDesligada,
    TurnoDoChat,
    conversa_uuid,
)

logger = logging.getLogger(__name__)

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


def fontes_para_auditoria(citadas: Sequence[FonteCitada]) -> tuple[FonteDaResposta, ...]:
    """Converte as fontes do contrato HTTP nas que a trilha grava.

    A conversão mora aqui, e não em `services/`, porque nenhum serviço importa
    `schemas` hoje — o contrato HTTP não deve vazar para dentro do domínio.

    `posicao` é copiada, não recalculada: é o mesmo inteiro que o modelo
    escreveu entre colchetes. Renumerar faria `mensagem_fonte.posicao` deixar de
    corresponder à citação, e a trilha perderia justamente o que a torna
    conferível.
    """
    return tuple(
        FonteDaResposta(
            chunk_id=f.chunk_id,
            arquivo_origem=f.arquivo_origem,
            posicao=f.posicao,
            score=f.score,
            projeto_codigo=f.projeto_id or None,
            tipo_documento=f.tipo_documento or None,
            secao=f.secao or None,
            trecho=f.trecho or None,
        )
        for f in citadas
    )


def classificar_sem_interferir(
    classificador: Callable[[str], tuple[str, float]] | None, texto: str
) -> tuple[str | None, float | None]:
    """A intenção prevista, ou (None, None) se não foi possível prevê-la.

    OBSERVAÇÃO, NÃO DECISÃO. O rótulo vai para `auditoria.mensagem.intencao` e
    não influencia busca, recusa nem resposta. Com F1-macro de 0,6736 contra os
    0,85 do RNF03, dar-lhe controle de fluxo erraria em cerca de um terço das
    interações; observando, ele torna o requisito mensurável sobre tráfego real
    — hoje a coluna é NULL em 100% das linhas — sem custar nada a quem pergunta.

    Qualquer falha é engolida de propósito: classificar é acessório, e um
    modelo com problema não pode derrubar a conversa.
    """
    if classificador is None:
        return None, None
    try:
        rotulo, confianca = classificador(texto)
    except Exception:
        logger.exception("Falha ao classificar a intenção; seguindo sem registrá-la.")
        return None, None
    return rotulo, float(confianca)


def registrar_turno_em_segundo_plano(
    repositorio: ConversaRepository | PersistenciaDesligada, turno: TurnoDoChat
) -> None:
    """Grava a trilha sem deixar a falha escapar.

    Tarefa de fundo do Starlette roda DEPOIS de a resposta ter sido enviada, e
    o `@app.exception_handler(Exception)` de `main.py` não a alcança — uma
    exceção aqui sobe pela pilha ASGI sem virar resposta nenhuma.

    Os dois ramos são separados de propósito: `ConversaNaoGravada` é dado
    incoerente, defeito nosso e sem valor no stack; qualquer outra coisa é
    banco ou MinIO fora, e aí o contexto completo importa.
    """
    try:
        repositorio.registrar_turno(turno)
    except ConversaNaoGravada as erro:
        logger.warning("Turno recusado pela validação da trilha: %s", erro)
    except Exception:
        logger.exception("Falha ao gravar a trilha da conversa %s.", turno.conversa_id)


@router.post("/chat", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    answerer: AnswerChatMessage = Depends(get_chat_answerer),
    repositorio: ConversaRepository | PersistenciaDesligada = Depends(get_conversa_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
    classificador=Depends(get_classificador_de_intencao),
) -> ChatResponse:
    inicio = time.monotonic()
    try:
        reply = answerer.answer(payload.message, payload.conversation_id)
    except ChatReceptionError as exc:
        # Requisição inválida (422) não é auditada: o manipulador de exceção
        # monta uma JSONResponse nova, sem as tarefas de fundo. Comportamento
        # herdado e intencional.
        details = _ERROR_DETAILS[exc.code]
        raise ChatAPIError(details.status_code, details.error, details.message) from exc

    # A ordem importa: as fontes saem do texto AINDA com os marcadores, e só
    # depois o texto é limpo. Invertida, não haveria como saber quais trechos o
    # modelo usou.
    fontes = fontes_citadas(reply.text, reply.fontes)
    resposta_texto = limpar_citacoes(reply.text)
    duracao_ms = int((time.monotonic() - inicio) * 1000)

    intencao, confianca = classificar_sem_interferir(classificador, payload.message)
    turno = _turno_da_conversa(
        payload, usuario, reply, resposta_texto, fontes, duracao_ms, intencao, confianca
    )
    if turno is not None:
        background_tasks.add_task(registrar_turno_em_segundo_plano, repositorio, turno)

    # `resposta_texto` é o mesmo que foi para a trilha: o que a pessoa viu é o
    # que fica registrado. A ligação afirmação↔fonte não se perde, porque vive
    # em `mensagem_fonte.posicao`.
    return ChatResponse(reply=resposta_texto, fontes=fontes)


def _turno_da_conversa(
    payload: ChatRequest,
    usuario: AuthenticatedUser,
    reply: ChatReply,
    resposta_texto: str,
    fontes: Sequence[FonteCitada],
    duracao_ms: int,
    intencao: str | None,
    confianca: float | None,
) -> TurnoDoChat | None:
    """O turno a gravar, ou None quando gravá-lo seria registrar uma falsidade.

    Dois motivos para desistir, e os dois preferem o silêncio a um dado errado:

    1. SEM IDENTIDADE. `domain_user_id` é None com `AZ1_AUTH_MODE=disabled` e
       quando `ResolveOrCreateUsuario` falhou — as duas engolidas de propósito
       em `dependencies.py`. Como `auditoria.conversa.usuario_id` é NOT NULL,
       seria preciso inventar um id; e inventar um id é literalmente o que
       produziu o `usuario_id = 0` que este projeto acabou de aposentar.
    2. IDENTIFICADOR INVÁLIDO. `conversa.id` é UUID.

    `intencao` é OBSERVADA, não usada: vem do classificador e vai para a linha
    do usuário — o CHECK `mensagem_papel_coerente` a recusa na do agente —, sem
    influenciar a resposta. Ver `classificar_sem_interferir`.
    """
    conversa_id = conversa_uuid(payload.conversation_id)
    if conversa_id is None:
        logger.warning(
            "conversation_id %r não é UUID; turno não registrado.", payload.conversation_id
        )
        return None

    if usuario.domain_user_id is None:
        logger.warning(
            "Sem identidade de domínio para %s; turno não registrado.", usuario.email
        )
        return None

    return TurnoDoChat(
        conversa_id=conversa_id,
        usuario_id=usuario.domain_user_id,
        prompt=payload.message,
        resposta=resposta_texto,
        resultado=reply.resultado,
        modelo=reply.modelo or None,
        tempo_processamento_ms=duracao_ms,
        intencao=intencao,
        confianca_intencao=confianca,
        fontes=fontes_para_auditoria(fontes),
    )
