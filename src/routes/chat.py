from __future__ import annotations

import logging
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, Depends

from az1_api.dependencies import (
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    require_authenticated_user,
)
from pln.entidades import extrair_entidades
from pln.intencao import DetectarIntencao, IntencaoDetectada
from rag.retriever import ResultadoBusca
from schemas.chat import ChatErrorCode, ChatRequest, ChatResponse, FonteCitada
from services.agente_service import AgenteDesligado, ExecutarIntencao, RespostaDoAgente, ResultadoAcao
from services.auth_service import AuthenticatedUser
from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    AnswerChatMessage,
    ChatReceptionError,
    ChatReceptionErrorCode,
    ChatReply,
    validar_mensagem,
)
from services.conversa_repository import (
    ConversaNaoGravada,
    ConversaRepository,
    FonteDaResposta,
    PersistenciaDesligada,
    TurnoDoChat,
    conversa_uuid,
)
from services.foco_da_busca import focar_busca

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
    numeros = {int(n) for grupo in _CITACAO.findall(texto) for n in grupo.split(",") if n.strip().isdigit()}
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


def recusar_conversa_alheia(
    repositorio: ConversaRepository | PersistenciaDesligada,
    conversation_id: str,
    usuario: AuthenticatedUser,
) -> None:
    """Barra o turno quando o `conversation_id` é de outra pessoa.

    Precisa vir ANTES de `answerer.answer()`, não depois: é ali que
    `_historico_do_banco` lê `auditoria.mensagem` pelo `conversa_id` sozinho,
    sem `usuario_id`. Enviando o UUID de uma conversa alheia, o histórico dela
    entrava no contexto do modelo e podia sair na resposta — o vazamento
    acontecia mesmo que nada fosse gravado depois.

    O identificador nasce no cliente (`crypto.randomUUID()` em `AgentPage.jsx`),
    então ele é entrada do usuário, e não prova de nada.

    Não engole exceção de banco de propósito. Deixar passar em caso de falha
    seria abrir exatamente o buraco que este porteiro fecha, e o `SELECT` do
    histórico, logo adiante, usa o mesmo pool: se este falhou, aquele falha
    também. Falhar fechado aqui é a diferença entre um 500 e um vazamento.
    """
    conversa_id = conversa_uuid(conversation_id)
    if conversa_id is None:
        # UUID inválido não alcança o banco: `_historico_do_banco` também o
        # recusa, e `_turno_da_conversa` já descarta o turno com aviso.
        return

    if usuario.domain_user_id is None:
        # Sem ligação com `portfolio.usuario` não há com o que comparar. O turno
        # tampouco será gravado (ver `_turno_da_conversa`), e o histórico volta
        # vazio porque nenhuma conversa aponta para um dono inexistente.
        return

    dono = repositorio.dono_da_conversa(str(conversa_id))
    if dono is not None and dono != usuario.domain_user_id:
        logger.warning(
            "Usuário %s tentou usar a conversa %s, que é de outro.",
            usuario.domain_user_id,
            conversa_id,
        )
        raise ChatAPIError(
            403,
            "forbidden",
            "Esta conversa pertence a outro usuário.",
        )


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


def classificar_sem_interferir(classificador: DetectarIntencao | None, texto: str) -> IntencaoDetectada | None:
    """A intenção detectada, ou None se não foi possível detectá-la.

    O que ela decide, e o que não decide: a intenção governa a AÇÃO do Agente
    — e, por consequência, se vale a pena perguntar ao modelo de linguagem.
    Ela não entra no prompt e não filtra a busca. Com F1-macro de 0,6736 contra
    os 0,85 do RNF03, deixá-la escolher o contexto da resposta erraria em cerca
    de um terço das interações; como gatilho de ação, um erro custa uma ação a
    menos e o RAG responde do mesmo jeito.

    Qualquer falha é engolida de propósito: sem detecção, `None` faz o fluxo
    cair no RAG. Um modelo com problema não pode derrubar a conversa.
    """
    if classificador is None:
        return None
    try:
        return classificador(texto)
    except Exception:
        logger.exception("Falha ao classificar a intenção; seguindo sem registrá-la.")
        return None


def executar_acao_sem_interferir(
    agente: ExecutarIntencao | AgenteDesligado,
    deteccao: IntencaoDetectada | None,
    texto: str,
) -> RespostaDoAgente | None:
    """A ação do Agente para esta mensagem, ou None se não há o que executar.

    Mesma postura de `classificar_sem_interferir`: qualquer falha do Agente é
    engolida e o fluxo segue para o RAG — agir é um recurso a mais, não pode
    ser um jeito novo de a conversa quebrar.

    `None` aqui é o que decide se o modelo de linguagem chega a ser chamado, e
    por isso o `except` importa mais do que parece: um Agente quebrado degrada
    para a conversa de sempre, e não para uma resposta vazia.
    """
    if deteccao is None:
        return None
    try:
        resposta = agente.executar(deteccao=deteccao, texto=texto)
    except Exception:
        logger.exception("Falha ao executar a ação do Agente; seguindo para o RAG.")
        return None
    return None if resposta.resultado is ResultadoAcao.SEM_ACAO else resposta


def texto_da_acao(resposta: RespostaDoAgente) -> str:
    """O texto que substitui a resposta do RAG quando o Agente agiu.

    `resposta.pendencias`/`resposta.projetos` já vêm filtrados por
    `ExecutarIntencao` — aqui só se formata o que chegou.
    """
    if resposta.resultado is ResultadoAcao.RECUSADA_FORA_DO_CATALOGO:
        # Texto literal da resposta-padrão 1.1 do material entregue pelo Metrô,
        # que a classifica como obrigatória e com prioridade sobre qualquer
        # tentativa de completar a informação. Não é redação nossa, e mudá-la
        # exige concordância do parceiro.
        return (
            "Essa pergunta não está relacionada ao Portfólio Organizacional e não "
            "possuo essa informação. Posso ajudá-lo com assuntos relacionados ao "
            "portfólio, programas e projetos."
        )

    if resposta.resultado is ResultadoAcao.PENDENCIAS:
        abertas = [p for p in resposta.pendencias if not p.resolvida]
        if not abertas:
            return "Não há pendências em aberto no momento."
        linhas = (
            f"- [{p.projeto_codigo}] {p.titulo}" + (f" (prazo {p.prazo.isoformat()})" if p.prazo else "")
            for p in abertas
        )
        return "Pendências que precisam de atenção:\n" + "\n".join(linhas)

    if resposta.resultado is ResultadoAcao.PROJETO:
        if not resposta.projetos:
            return "Não encontrei o projeto informado."
        linhas = (
            f"- {p.codigo} — {p.nome}: {p.percentual_avanco:.0f}% concluído "
            f"(previsto {p.percentual_previsto:.0f}%), status {p.status}"
            for p in resposta.projetos
        )
        return "Situação do(s) projeto(s):\n" + "\n".join(linhas)

    return ""


_RESULTADO_POR_ACAO = {
    ResultadoAcao.RECUSADA_FORA_DO_CATALOGO: "recusada",
    ResultadoAcao.PENDENCIAS: "sucesso",
    ResultadoAcao.PROJETO: "sucesso",
}


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
    classificador: DetectarIntencao | None = Depends(get_classificador_de_intencao),
    agente: ExecutarIntencao | AgenteDesligado = Depends(get_agente),
) -> ChatResponse:
    """Classifica, age se houver ação, e só então pergunta ao modelo.

    ESTA ORDEM É O CONTRATO, e por muito tempo não foi o código. O handler
    chamava `answerer.answer` primeiro e classificava depois, de modo que todo
    turno em que o Agente agia — pendências, situação de projeto ou recusa —
    pagava uma geração no Gemini e uma busca vetorial cujo resultado era
    descartado na linha seguinte.

    No caso da recusa isso não era só desperdício: a Seção 2.1 do Projeto.md
    especifica recusar pedidos fora do escopo "antes mesmo de consultar as
    fontes de dados", e o caso crítico 1 da Seção 2.2.3 modela a classificação
    antes do roteamento. Consultar as fontes para depois jogar fora a resposta
    é o oposto do que o artefato descreve.
    """
    resultado = responder_turno(
        payload=payload,
        usuario=usuario,
        answerer=answerer,
        repositorio=repositorio,
        classificador=classificador,
        agente=agente,
    )

    if resultado.turno is not None:
        background_tasks.add_task(registrar_turno_em_segundo_plano, repositorio, resultado.turno)

    # `resultado.texto` é o mesmo que foi para a trilha: o que a pessoa viu é o
    # que fica registrado. A ligação afirmação↔fonte não se perde, porque vive
    # em `mensagem_fonte.posicao`.
    return ChatResponse(reply=resultado.texto, fontes=resultado.fontes)


def _resultado_do_turno(reply: ChatReply | None, resposta_do_agente: RespostaDoAgente | None) -> tuple[str, str | None]:
    """O par `resultado`/`modelo` de `auditoria.mensagem`, em um lugar só.

    Vive separado porque dois chamadores precisam dele: `_turno_da_conversa`,
    para gravar, e `responder_turno`, para informar ao servidor MCP se a
    resposta foi uma recusa. Se cada um derivasse por conta própria, bastaria
    um acrescentar um caso novo para o outro passar a mentir.
    """
    if resposta_do_agente is not None:
        return _RESULTADO_POR_ACAO[resposta_do_agente.resultado], None
    assert reply is not None  # os dois ramos são exclusivos, por construção
    return reply.resultado, reply.modelo or None


@dataclass(frozen=True)
class TurnoRespondido:
    """O que um turno produziu, sem decidir como ele será persistido.

    Separar produzir de gravar existe porque os dois chamadores de
    `responder_turno` gravam de formas diferentes: a rota HTTP agenda a escrita
    em `BackgroundTasks`, para não fazer o usuário esperar por ela; o servidor
    MCP grava em linha, porque ali não há resposta HTTP cujo tempo precise ser
    protegido.
    """

    texto: str
    fontes: list[FonteCitada]
    turno: TurnoDoChat | None
    # `sucesso`, `esclarecimento`, `recusada` ou `falha`. Informado mesmo quando
    # `turno` é None, porque quem chama pode precisar saber que houve recuo sem
    # depender de a trilha ter sido gravada.
    resultado: str


def responder_turno(
    *,
    payload: ChatRequest,
    usuario: AuthenticatedUser,
    answerer: AnswerChatMessage,
    repositorio: ConversaRepository | PersistenciaDesligada,
    classificador: DetectarIntencao | None,
    agente: ExecutarIntencao | AgenteDesligado,
) -> TurnoRespondido:
    """O percurso de um turno, compartilhado entre a rota HTTP e o servidor MCP.

    Extraída do handler para que `src/mcp_servidor/` exerça EXATAMENTE este
    caminho, e não uma reimplementação dele. Com duas orquestrações próprias, a
    ordem descrita no docstring de `send_chat_message` valeria para um canal só,
    e a divergência apareceria como resposta diferente para a mesma pergunta
    conforme por onde ela entrou.

    Levanta `ChatAPIError`, que é vocabulário HTTP, e isso é dívida reconhecida:
    o lugar próprio desta função é `services/`. Ela ficou aqui porque os seis
    auxiliares que chama já moram neste módulo, e movê-los junto é refatoração
    de arquivo coberto por teste — trabalho que não cabia no mesmo passo em que
    o caminho MCP é validado pela primeira vez. Quem chama de fora do HTTP
    traduz a exceção, como `mcp_servidor/servidor.py` faz.
    """

    inicio = time.monotonic()

    # Validar ANTES de classificar. Sem isto, mensagem vazia chegaria ao
    # classificador, e o 422 passaria a depender do que o modelo achasse de uma
    # string em branco.
    #
    # Requisição inválida (422) não é auditada: o manipulador de exceção monta
    # uma JSONResponse nova, sem as tarefas de fundo. Comportamento herdado e
    # intencional.
    try:
        mensagem = validar_mensagem(payload.message)
    except ChatReceptionError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise ChatAPIError(details.status_code, details.error, details.message) from exc

    # Antes de classificar e de qualquer leitura de histórico: ver o docstring
    # de `recusar_conversa_alheia`.
    recusar_conversa_alheia(repositorio, payload.conversation_id, usuario)

    deteccao = classificar_sem_interferir(classificador, mensagem)
    resposta_do_agente = executar_acao_sem_interferir(agente, deteccao, mensagem)

    if resposta_do_agente is not None:
        # Nenhuma chamada ao modelo e nenhuma busca: não há o que citar quando
        # a resposta veio do portfólio ou é uma recusa.
        reply = None
        resposta_texto = texto_da_acao(resposta_do_agente)
        fontes: list[FonteCitada] = []
    else:
        try:
            # A classificação chega à LLM aqui — não como afirmação dentro
            # do prompt, mas escolhendo EM QUE DOCUMENTOS buscar. Um rótulo
            # errado custa uma consulta vetorial a mais, porque o buscador
            # recua para a busca ampla; dentro do prompt, custaria a resposta.
            # `resposta_do_agente` é None aqui por construção — este ramo só
            # roda quando o Agente NÃO agiu —, então as entidades se extraem
            # da mensagem. A extração é por regra (`SYN-\d{2}`), então o
            # código do projeto entra no foco mesmo quando a intenção não
            # sugere tipo de documento: a confiabilidade dele não depende do
            # F1 do classificador.
            foco = focar_busca(deteccao, extrair_entidades(mensagem))
            reply = answerer.answer(mensagem, payload.conversation_id, foco=foco)
        except ChatReceptionError as exc:
            details = _ERROR_DETAILS[exc.code]
            raise ChatAPIError(details.status_code, details.error, details.message) from exc

        # A ordem importa: as fontes saem do texto AINDA com os marcadores, e
        # só depois o texto é limpo. Invertida, não haveria como saber quais
        # trechos o modelo usou.
        fontes = fontes_citadas(reply.text, reply.fontes)
        resposta_texto = limpar_citacoes(reply.text)

    duracao_ms = int((time.monotonic() - inicio) * 1000)

    turno = _turno_da_conversa(
        payload,
        usuario,
        reply,
        resposta_texto,
        fontes,
        duracao_ms,
        deteccao,
        resposta_do_agente,
    )

    resultado_do_turno, _ = _resultado_do_turno(reply, resposta_do_agente)
    return TurnoRespondido(texto=resposta_texto, fontes=fontes, turno=turno, resultado=resultado_do_turno)


def _turno_da_conversa(
    payload: ChatRequest,
    usuario: AuthenticatedUser,
    reply: ChatReply | None,
    resposta_texto: str,
    fontes: Sequence[FonteCitada],
    duracao_ms: int,
    deteccao: IntencaoDetectada | None,
    resposta_do_agente: RespostaDoAgente | None,
) -> TurnoDoChat | None:
    """O turno a gravar, ou None quando gravá-lo seria registrar uma falsidade.

    Dois motivos para desistir, e os dois preferem o silêncio a um dado errado:

    1. SEM IDENTIDADE. `domain_user_id` é None com `AZ1_AUTH_MODE=disabled` e
       quando `ResolveOrCreateUsuario` falhou — as duas engolidas de propósito
       em `dependencies.py`. Como `auditoria.conversa.usuario_id` é NOT NULL,
       seria preciso inventar um id; e inventar um id é literalmente o que
       produziu o `usuario_id = 0` que este projeto acabou de aposentar.
    2. IDENTIFICADOR INVÁLIDO. `conversa.id` é UUID.

    `intencao` vai para a linha do usuário — o CHECK `mensagem_papel_coerente`
    a recusa na do agente — e grava a previsão CRUA do modelo, não o que sobra
    da rejeição. A distinção importa: a regra de rejeição é reconstituível a
    partir de `confianca_intencao` e do limiar, enquanto o argmax descartado
    não é. Guardar o cru é o que permitirá recalibrar o limiar sobre tráfego
    real, que é a razão de a coluna existir.

    `resultado`/`modelo` vêm do RAG por padrão, mas quando o Agente agiu
    (`resposta_do_agente` não é None) são os dele: `recusada` para
    fora-do-catálogo, `sucesso` para uma ação de portfólio executada, sem
    `modelo` nenhum por trás — e, desde que a classificação passou a vir antes,
    sem geração nenhuma por trás também, motivo pelo qual `reply` é None nesse
    ramo.
    """
    conversa_id = conversa_uuid(payload.conversation_id)
    if conversa_id is None:
        logger.warning("conversation_id %r não é UUID; turno não registrado.", payload.conversation_id)
        return None

    if usuario.domain_user_id is None:
        logger.warning("Sem identidade de domínio para %s; turno não registrado.", usuario.email)
        return None

    resultado, modelo = _resultado_do_turno(reply, resposta_do_agente)

    return TurnoDoChat(
        conversa_id=conversa_id,
        usuario_id=usuario.domain_user_id,
        prompt=payload.message,
        resposta=resposta_texto,
        resultado=resultado,
        modelo=modelo,
        tempo_processamento_ms=duracao_ms,
        intencao=deteccao.prevista if deteccao is not None else None,
        confianca_intencao=deteccao.confianca if deteccao is not None else None,
        fontes=fontes_para_auditoria(fontes),
    )
