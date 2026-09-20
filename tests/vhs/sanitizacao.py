"""Remoção de segredos antes de a gravação tocar o disco.

O item 3 do contrato da Seção 6.4.3 nomeia o que sai: `authorization`,
`x-goog-api-key`, cookies e parâmetros de chave na query, com callbacks que
alcancem também corpos e cabeçalhos de resposta — a proteção revisada "em
ambos os sentidos". A prova de compatibilidade feita antes deste módulo mostrou
que, sem esses callbacks, o `Authorization` enviado e o `Set-Cookie` recebido
ficam legíveis no arquivo YAML. É essa a falha que TI-50 procura.

Há duas defesas aqui, e elas cobrem coisas diferentes:

1. **Por nome** — cabeçalhos e parâmetros de query conhecidos são removidos pelo
   nome, independentemente do valor que carreguem.
2. **Por valor** — os segredos do ambiente são procurados literalmente em URI,
   corpo de requisição e corpo de resposta. É o que pega a chave que o SDK
   resolveu pôr em um cabeçalho novo, ou que o provedor devolveu ecoada.

A primeira sozinha não basta, porque depende de prever o nome. A segunda
sozinha também não, porque em CI o segredo pode não estar no ambiente de quem
grava. Juntas, cobrem o previsto e o que escapou da previsão.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MARCA = "[VHS:REMOVIDO]"

# Cabeçalhos que carregam credencial em algum dos SDKs em uso, mais os genéricos
# de sessão. `x-goog-api-key` é o do google-genai; a Deepgram usa `authorization`.
CABECALHOS_PROIBIDOS: tuple[str, ...] = (
    "authorization",
    "proxy-authorization",
    "x-goog-api-key",
    "x-api-key",
    "api-key",
    "cookie",
    "set-cookie",
    "dg-token",
)

# Parâmetros de query que carregam chave. O google-genai aceita `?key=`.
PARAMETROS_PROIBIDOS: tuple[str, ...] = (
    "key",
    "api_key",
    "apikey",
    "access_token",
    "token",
    "signature",
    "x-amz-signature",
)

# Variáveis do .env.example que guardam segredo. A URI de banco entra na lista
# porque o plano proíbe publicá-la junto com token e URL assinada.
VARIAVEIS_SENSIVEIS: tuple[str, ...] = (
    "DEEPGRAM_API_KEY",
    "GEMINI_API_KEY",
    "SUPABASE_DB_URL",
    "SUPABASE_ANON_KEY",
    "DATABASE_URL",
    "AUDIO_STORAGE_ACCESS_KEY",
    "AUDIO_STORAGE_SECRET_KEY",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_WEBHOOK_CHANNEL_TOKEN",
    "MS_WEBHOOK_CLIENT_STATE",
    "GITLAB_TOKEN",
)

# Valor curto demais não é segredo, é coincidência: procurar "K" dentro de um
# corpo de resposta redigiria o texto inteiro.
TAMANHO_MINIMO_DE_SEGREDO = 8


def segredos_do_ambiente(variaveis: Iterable[str] = VARIAVEIS_SENSIVEIS) -> tuple[str, ...]:
    """Valores de segredo presentes no ambiente, prontos para redação literal."""
    valores = {os.environ.get(nome, "").strip() for nome in variaveis}
    return tuple(sorted(valor for valor in valores if len(valor) >= TAMANHO_MINIMO_DE_SEGREDO))


def _redigir_texto(texto: str, segredos: Sequence[str]) -> str:
    for segredo in segredos:
        texto = texto.replace(segredo, MARCA)
    return texto


def _redigir_corpo(corpo: bytes | str | None, segredos: Sequence[str]) -> bytes | str | None:
    """Redige o corpo preservando o tipo, que o VCR.py usa na serialização.

    Corpo binário — o áudio enviado ao STT, o WAV devolvido pelo TTS — passa
    inalterado quando nenhum segredo aparece nele, e é isso que mantém o
    conteúdo da gravação fiel ao que o provedor viu.
    """
    if corpo is None or not segredos:
        return corpo
    if isinstance(corpo, bytes):
        for segredo in segredos:
            corpo = corpo.replace(segredo.encode("utf-8"), MARCA.encode("utf-8"))
        return corpo
    return _redigir_texto(corpo, segredos)


def _uri_sanitizada(uri: str, segredos: Sequence[str]) -> str:
    partes = urlsplit(uri)
    query = [
        (nome, MARCA if nome.lower() in PARAMETROS_PROIBIDOS else valor)
        for nome, valor in parse_qsl(partes.query, keep_blank_values=True)
    ]
    limpa = urlunsplit(partes._replace(query=urlencode(query)))
    return _redigir_texto(limpa, segredos)


def sanitizar_requisicao(segredos: Sequence[str] = ()) -> Callable[[object], object]:
    """Callback de `before_record_request`.

    O VCR.py aplica este callback tanto ao gravar quanto ao casar uma requisição
    com a fita (`Cassette._responses`). É por isso que remover o `Authorization`
    não quebra o replay: a requisição de agora é redigida do mesmo jeito que a
    de ontem antes da comparação.
    """

    def callback(requisicao):  # noqa: ANN001 - o tipo é vcr.request.Request
        for nome in CABECALHOS_PROIBIDOS:
            requisicao.headers.pop(nome, None)
        requisicao.uri = _uri_sanitizada(requisicao.uri, segredos)
        requisicao.body = _redigir_corpo(requisicao.body, segredos)
        return requisicao

    return callback


def sanitizar_resposta(segredos: Sequence[str] = ()) -> Callable[[dict], dict]:
    """Callback de `before_record_response`.

    A resposta chega como dicionário, com cabeçalhos em listas de valores. O
    `Set-Cookie` sai por nome; o resto do que for segredo conhecido sai por
    valor, inclusive dentro do corpo.
    """

    def callback(resposta: dict) -> dict:
        cabecalhos = resposta.get("headers") or {}
        resposta["headers"] = {
            nome: [_redigir_texto(str(valor), segredos) for valor in valores]
            for nome, valores in cabecalhos.items()
            if nome.lower() not in CABECALHOS_PROIBIDOS
        }

        corpo = resposta.get("body")
        if isinstance(corpo, dict) and "string" in corpo:
            corpo["string"] = _redigir_corpo(corpo["string"], segredos)

        return resposta

    return callback


def varrer_segredos(raiz: Path, segredos: Sequence[str] = ()) -> list[str]:
    """Procura vazamento nos arquivos gravados; devolve os achados legíveis.

    Serve à evidência de TI-50, que pede varredura dos arquivos de sucesso e de
    falha. Procura os nomes proibidos e, se houver, os valores de segredo.
    """
    achados: list[str] = []
    alvos = [*CABECALHOS_PROIBIDOS, *segredos]

    for arquivo in sorted(raiz.rglob("*.yaml")):
        bruto = arquivo.read_text(encoding="utf-8", errors="replace").lower()
        for alvo in alvos:
            if alvo.lower() in bruto:
                achados.append(f"{arquivo.relative_to(raiz)}: {alvo}")

    return achados
