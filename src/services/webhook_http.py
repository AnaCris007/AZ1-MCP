"""Chamadas HTTP e erros compartilhados pelas ferramentas de linha de comando.

Os dois provedores têm fluxos de autorização diferentes — laço de retorno local
no Google, código de dispositivo na Microsoft —, mas a chamada HTTP em si e o
formato do erro são os mesmos. Ficam aqui para que cada script trate só o que é
próprio do seu provedor.

Usa apenas a biblioteca padrão. É deliberado: as bibliotecas oficiais dos dois
resolveriam isto em menos linhas, mas trariam árvores de dependência grandes para
ferramentas operacionais que rodam algumas vezes por semana, fora do caminho de
execução da API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ErroDeOperacao(Exception):
    """Falha esperada, comunicada ao operador sem traceback."""


class ErroHTTP(ErroDeOperacao):
    """Resposta de erro do provedor, com o corpo já interpretado.

    O corpo importa: os endpoints de autorização usam `400` tanto para "ainda não
    autorizado, continue perguntando" quanto para falhas definitivas, e só o campo
    `error` do JSON distingue os dois.
    """

    def __init__(self, status: int, corpo: Any, url: str) -> None:
        self.status = status
        self.corpo = corpo
        self.url = url
        detalhe = json.dumps(corpo, indent=2, ensure_ascii=False) if isinstance(corpo, dict) else str(corpo)
        super().__init__(f"{url} devolveu {status}:\n{detalhe}")

    @property
    def codigo(self) -> str:
        return self.corpo.get("error", "") if isinstance(self.corpo, dict) else ""


def pedir(
    url: str,
    *,
    dados: Any = None,
    token: str | None = None,
    metodo: str = "GET",
    formulario: bool = False,
) -> dict[str, Any]:
    """Faz uma chamada e devolve o JSON da resposta, ou `{}` se o corpo vier vazio.

    `formulario=True` envia `application/x-www-form-urlencoded`, exigido pelos
    endpoints de token dos dois provedores; o resto da API dos dois fala JSON.
    """
    corpo = None
    cabecalhos = {"Accept": "application/json"}

    if dados is not None:
        if formulario:
            corpo = urllib.parse.urlencode(dados).encode()
            cabecalhos["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            corpo = json.dumps(dados).encode()
            cabecalhos["Content-Type"] = "application/json"

    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"

    requisicao = urllib.request.Request(url, data=corpo, headers=cabecalhos, method=metodo)

    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else {}
    except urllib.error.HTTPError as exc:
        texto = exc.read().decode("utf-8", errors="replace")
        try:
            interpretado: Any = json.loads(texto)
        except json.JSONDecodeError:
            interpretado = texto
        raise ErroHTTP(exc.code, interpretado, url) from exc
    except urllib.error.URLError as exc:
        raise ErroDeOperacao(f"Não foi possível alcançar {url}: {exc.reason}") from exc
