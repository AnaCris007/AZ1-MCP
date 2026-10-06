"""Guarda de chave de API do caminho MCP.

POR QUE UM ESQUEMA SÓ PARA O /mcp
---------------------------------
O resto da API valida um JWT por requisição (`SupabaseTokenVerifier`), e esse
token pressupõe um usuário que fez login no navegador. O conector do Copilot
Studio não tem navegador nem usuário: ele é um cliente de serviço chamando de
fora. Os dois esquemas convivem porque atendem a chamadores diferentes, e a
guarda daqui é montada APENAS no sub-aplicativo do `/mcp`.

O QUE ESTA GUARDA NÃO FAZ, E PRECISA SER DITO
---------------------------------------------
Ela autentica o CLIENTE, não a PESSOA. Com uma chave única, toda chamada chega
como a mesma identidade, e `auditoria.mensagem` registra um usuário só. A
consequência está na Seção 5.2 do GuiaImplantacaoCopilotStudio.md e define o
limite de uso: piloto com massa sintética, não acervo real do PMO. Levantar
essa restrição exige OAuth com o Entra ID, que depende de um registro de
aplicativo no diretório do parceiro.

ROTAÇÃO
-------
`AZ1_MCP_API_KEY` aceita mais de uma chave separada por vírgula. Existe por um
motivo operacional: a chave vive em dois lugares (as variáveis do servidor e a
*connection* do Power Platform) que são atualizados em momentos distintos. Sem
aceitar duas ao mesmo tempo, toda troca teria uma janela de indisponibilidade.
"""

from __future__ import annotations

import hmac
import os

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

CABECALHO = "x-api-key"
VARIAVEL = "AZ1_MCP_API_KEY"


def chaves_aceitas() -> tuple[str, ...]:
    """As chaves válidas, lidas do ambiente a cada chamada.

    Ler a cada chamada, e não uma vez na importação, é o que permite rotacionar
    sem reiniciar o contêiner em plataformas que injetam variável nova no
    processo. Custa um `os.environ` por requisição, que é irrelevante diante de
    uma chamada ao modelo.
    """
    bruto = os.environ.get(VARIAVEL, "")
    return tuple(parte.strip() for parte in bruto.split(",") if parte.strip())


def chave_valida(apresentada: str | None) -> bool:
    """Compara em tempo constante contra cada chave aceita.

    `hmac.compare_digest` em vez de `==` porque a comparação ingênua retorna no
    primeiro byte diferente, e a diferença de tempo entre uma chave que erra no
    primeiro caractere e outra que erra no último é mensurável por um atacante
    remoto paciente. O custo de usar a forma correta é zero.
    """
    if not apresentada:
        return False
    return any(hmac.compare_digest(apresentada, aceita) for aceita in chaves_aceitas())


class ExigirChaveDeApi:
    """Middleware ASGI que barra a requisição antes de ela chegar ao MCP.

    É middleware, e não dependência do FastAPI, porque o `/mcp` é um
    sub-aplicativo ASGI montado inteiro: não há uma rota nossa onde pendurar um
    `Depends`. Barrar aqui também significa que nenhuma mensagem do protocolo
    MCP chega a ser interpretada sem chave, o que é a ordem correta.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not chaves_aceitas():
            # Sem chave configurada o servidor não "abre": ele recusa tudo. O
            # oposto — tratar ausência de configuração como ausência de
            # exigência — é como endpoints internos acabam expostos.
            await self._recusar(scope, receive, send, 503, "mcp_sem_chave", "Servidor MCP sem chave configurada.")
            return

        if not chave_valida(Request(scope).headers.get(CABECALHO)):
            await self._recusar(scope, receive, send, 401, "mcp_nao_autorizado", "Chave de API ausente ou inválida.")
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _recusar(scope: Scope, receive: Receive, send: Send, status: int, erro: str, mensagem: str) -> None:
        resposta = JSONResponse({"error": erro, "message": mensagem}, status_code=status)
        await resposta(scope, receive, send)


class NormalizarCaminhoMcp:
    """Faz `/mcp` responder sem passar por redirecionamento.

    O roteador do Starlette responde `/mcp` com 307 para `/mcp/`, porque o
    sub-aplicativo está montado com uma rota na raiz. O `curl` preserva o
    `x-api-key` ao seguir, mas preservar cabeçalho personalizado através de
    redirecionamento é comportamento de cliente, não garantia do protocolo: um
    cliente que o descarte receberia 401 sem explicação possível.

    Reescrever o caminho ANTES do roteamento tira o conector dessa dependência,
    e faz a URL documentada funcionar exatamente como está escrita.
    """

    def __init__(self, app: ASGIApp, prefixo: str = "/mcp") -> None:
        self.app = app
        self.prefixo = prefixo

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == self.prefixo:
            scope = {**scope, "path": f"{self.prefixo}/"}
        await self.app(scope, receive, send)
