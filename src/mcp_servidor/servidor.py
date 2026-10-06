"""Servidor MCP do AZ1, para conectar o agente do Copilot Studio.

POR QUE `mcp_servidor` E NÃO `mcp`
----------------------------------
O nome óbvio seria `src/mcp/`, e ele quebraria tudo. O `fastmcp` depende de um
pacote instalado chamado `mcp`, e como este projeto põe `src/` no caminho de
importação, um `src/mcp/` sombrearia a dependência: o `fastmcp` importaria o
nosso módulo achando que é a biblioteca dele.

UMA FERRAMENTA DE ALTO NÍVEL, E NÃO QUATRO DE BAIXO
---------------------------------------------------
`responder_consulta` recebe a pergunta em linguagem natural e devolve a
resposta pronta. A tentação é decompor — uma ferramenta para buscar trechos,
outra para listar projetos — e deixar o orquestrador do Copilot Studio montar a
resposta. Isso desmonta o produto, porque o valor do AZ1 não está nas peças
isoladas e sim na sequência: a intenção é classificada por um modelo com
acurácia medida, a classificação FILTRA a busca em vez de instruir o modelo, e
quando a evidência não sustenta uma resposta o sistema RECUA.

Entregando trechos crus a um orquestrador externo, quem decide se há evidência
suficiente passa a ser o modelo dele, e o recuo — que é a defesa contra o risco
AM8 — deixa de existir sem que nada falhe visivelmente.

O CAMPO `recuou`
----------------
Existe para que o agente não tente melhorar uma recusa. Quando vier verdadeiro,
a instrução do agente deve ser repassar o texto como está.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from fastmcp import FastMCP

from az1_api.dependencies import (
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    get_usuario_resolver,
)
from routes.chat import ChatAPIError, registrar_turno_em_segundo_plano, responder_turno
from schemas.chat import ChatRequest
from services.auth_service import AuthenticatedUser

logger = logging.getLogger(__name__)

VARIAVEL_IDENTIDADE = "AZ1_MCP_USUARIO_EMAIL"

mcp = FastMCP("AZ1")


@dataclass(frozen=True)
class RespostaDaFerramenta:
    """Contrato de saída, achatado de propósito.

    O Copilot Studio apresenta ao agente o esquema que a ferramenta declara, e
    estruturas aninhadas levam o orquestrador a recombinar campos. Quanto mais
    plano, menos espaço para ele reescrever o que já veio pronto.
    """

    resposta: str
    fontes: list[dict[str, str]]
    recuou: bool


def identidade_de_servico() -> AuthenticatedUser:
    """A identidade sob a qual as chamadas do conector são registradas.

    Com chave de API não existe usuário final, e inventar um seria exatamente o
    que o docstring de `_turno_da_conversa` chama de registrar uma falsidade.
    Então: se `AZ1_MCP_USUARIO_EMAIL` apontar para um usuário de serviço já
    existente em `portfolio.usuario`, o turno é gravado em nome dele; se não,
    `domain_user_id` fica None e `_turno_da_conversa` desiste de gravar, com
    aviso em log. A resposta ao usuário sai nos dois casos.

    Esta função é a fronteira que torna barata a troca para OAuth: quando o
    conector passar a mandar token do Entra, é aqui que a identidade real
    entra, e nem as ferramentas nem a persistência mudam.
    """
    email = os.environ.get(VARIAVEL_IDENTIDADE, "").strip()
    usuario = AuthenticatedUser(
        subject=f"mcp:{email or 'anonimo'}",
        email=email,
        name="Conector MCP",
        provider="mcp",
    )
    if not email:
        return usuario

    resolver = get_usuario_resolver()
    if resolver is None:
        logger.warning("Sem banco para resolver %s; turnos do MCP não serão gravados.", email)
        return usuario

    try:
        resolvido = resolver.resolve(usuario)
    except Exception:  # noqa: BLE001 - a resposta não pode depender da auditoria
        logger.warning("Falha ao resolver o usuário de serviço %s.", email, exc_info=True)
        return usuario
    return resolvido


@mcp.tool
def responder_consulta(pergunta: str, id_conversa: str = "") -> RespostaDaFerramenta:
    """Responde uma pergunta sobre o portfólio de empreendimentos do PMO.

    Use esta ferramenta para TODA pergunta de domínio: situação de projeto,
    prazos, marcos, riscos, pendências, documentos e normativos. Ela devolve a
    resposta final com as fontes consultadas. Quando `recuou` vier verdadeiro,
    repasse o texto como está: significa que não há evidência suficiente na
    base, e reformular a resposta inventaria informação.

    Args:
        pergunta: A pergunta do usuário, em português, em linguagem natural.
        id_conversa: Identificador UUID da conversa, para manter o contexto
            entre perguntas. Deixe vazio para iniciar uma conversa nova.
    """
    payload = ChatRequest(message=pergunta, conversation_id=id_conversa)
    repositorio = get_conversa_repository()

    try:
        resultado = responder_turno(
            payload=payload,
            usuario=identidade_de_servico(),
            answerer=get_chat_answerer(),
            repositorio=repositorio,
            classificador=get_classificador_de_intencao(),
            agente=get_agente(),
        )
    except ChatAPIError as exc:
        # `ChatAPIError` é vocabulário HTTP e não atravessa o protocolo MCP.
        # Traduzir aqui é o preço de `responder_turno` ainda morar em `routes/`,
        # e está registrado no docstring dela.
        raise ValueError(exc.message) from exc

    if resultado.turno is not None:
        # Em linha, e não em segundo plano: fora do ciclo de requisição do
        # FastAPI não há `BackgroundTasks`, e perder a trilha em silêncio seria
        # pior que esperar alguns milissegundos pela escrita.
        registrar_turno_em_segundo_plano(repositorio, resultado.turno)

    return RespostaDaFerramenta(
        resposta=resultado.texto,
        fontes=[
            {
                "arquivo": fonte.arquivo_origem,
                "secao": fonte.secao,
                "projeto": fonte.projeto_id,
                "tipo_documento": fonte.tipo_documento,
            }
            for fonte in resultado.fontes
        ],
        # Do campo que a auditoria grava, e não de heurística sobre a lista de
        # fontes estar vazia: uma resposta do portfólio também não cita fonte, e
        # seria lida como recuo.
        recuou=resultado.resultado == "recusada",
    )


def aplicativo_asgi():
    """O sub-aplicativo a montar em `/mcp`, em modo sem estado.

    Sem estado porque o Copilot Studio trata cada chamada de ferramenta como
    independente e não mantém sessão MCP entre elas. Com estado, o servidor
    guardaria sessões que ninguém retoma.
    """
    return mcp.http_app(path="/", stateless_http=True)
