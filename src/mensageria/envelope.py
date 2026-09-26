"""Serialização do envelope canônico para trânsito no barramento.

O `EventoWebhook` já é o envelope acordado com a Seção 6.4: os seis campos que
o produtor grava são exatamente os que o consumidor lê. Serializar é, então,
apenas transportá-lo sem perder nenhum — em especial a `versao` (que diz ao
consumidor como interpretar a mensagem) e a `marca_de_tempo` com fuso, que um
descuido de formatação transformaria em datetime ingênuo do outro lado.

O formato é JSON e não pickle de propósito: o consumidor é um processo separado,
que pode subir de uma imagem em versão diferente do produtor. JSON é um contrato
legível e independente de versão de Python; pickle amarraria os dois processos à
mesma árvore de classes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime

from services.webhook_service import EventoWebhook


class EnvelopeInvalido(ValueError):
    """Os bytes recebidos não formam um envelope desserializável.

    Existe como tipo próprio para que o consumidor consiga distinguir "não
    consegui ler a mensagem" (vai direto para a fila morta, sem reentrega) de
    uma falha de processamento (que pode ser reentregue).
    """


def serializar(evento: EventoWebhook) -> bytes:
    """Converte o envelope em bytes JSON, preservando os seis campos.

    A `marca_de_tempo` vira ISO 8601 COM fuso (o `isoformat` de um datetime
    tz-aware inclui o deslocamento); `conteudo`, que é um `Mapping`, vira um
    `dict` simples para o `json.dumps`. `ensure_ascii=False` mantém acentos
    legíveis no corpo em trânsito, sem alterar a semântica.
    """
    corpo = {
        "identificador": evento.identificador,
        "tipo": evento.tipo,
        "versao": evento.versao,
        "marca_de_tempo": evento.marca_de_tempo.isoformat(),
        "correlacao": evento.correlacao,
        "conteudo": dict(evento.conteudo),
    }
    return json.dumps(corpo, ensure_ascii=False).encode("utf-8")


def desserializar(dados: bytes) -> EventoWebhook:
    """Reconstrói o envelope a partir dos bytes, ou levanta `EnvelopeInvalido`.

    A `marca_de_tempo` volta a ser um datetime via `fromisoformat`, que preserva
    o fuso que `serializar` gravou. Qualquer defeito — JSON inválido, campo
    ausente, data em formato impossível — vira `EnvelopeInvalido`, para que o
    consumidor trate a mensagem como irrecuperável em vez de entrar em laço de
    reentrega.
    """
    try:
        bruto = json.loads(dados)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise EnvelopeInvalido(f"payload não é JSON desserializável: {exc}") from exc

    if not isinstance(bruto, Mapping):
        raise EnvelopeInvalido("payload JSON não é um objeto com os campos do envelope")

    try:
        marca = datetime.fromisoformat(bruto["marca_de_tempo"])
        return EventoWebhook(
            identificador=bruto["identificador"],
            tipo=bruto["tipo"],
            versao=bruto["versao"],
            marca_de_tempo=marca,
            correlacao=bruto["correlacao"],
            conteudo=bruto["conteudo"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EnvelopeInvalido(f"envelope incompleto ou com campo inválido: {exc}") from exc
