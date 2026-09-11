from __future__ import annotations

import hmac
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from services.webhook_service import (
    VERSAO_ENVELOPE,
    EventoWebhook,
    RegistroConexoes,
    WebhookError,
    WebhookErrorCode,
)

PROVEDOR = "google_drive"

# Os estados que o Drive emite. `sync` é a mensagem de abertura do canal, enviada
# uma vez logo após a criação; `change` é o que chega do feed de mudanças. Os
# demais valem para `files.watch`, que não usamos — ficam catalogados para não
# caírem no TI-40 como se fossem desconhecidos.
ESTADOS_CONHECIDOS = frozenset({"sync", "add", "remove", "update", "trash", "untrash", "change"})

# `sync` fica de fora de propósito: é o aviso de que o canal foi aberto, e nada
# mudou no acervo. Ele cai no caso TI-40 — registrado e encerrado sem efeito —,
# que é exatamente o tratamento que a documentação do Google recomenda.
TIPOS_PROCESSAVEIS = frozenset(f"drive.{estado}" for estado in ESTADOS_CONHECIDOS - {"sync"})


def _cabecalhos_normalizados(cabecalhos: Mapping[str, str]) -> dict[str, str]:
    """Rebaixa as chaves para minúsculas.

    Cabeçalho HTTP não diferencia maiúsculas de minúsculas, e cada cliente
    escreve `X-Goog-Channel-ID` de um jeito. O Starlette já entrega minúsculo,
    mas quem constrói a entrega num teste não tem obrigação de saber disso.
    """
    return {chave.lower(): valor for chave, valor in cabecalhos.items()}


@dataclass(frozen=True)
class TradutorDrive:
    """Converte a notificação do Google Drive no envelope canônico.

    O contraste com `TradutorGraph` é o que justifica a assinatura da porta: o
    Graph manda tudo no corpo e ignora os cabeçalhos; o Drive faz o oposto — o
    corpo chega **vazio** (`Content-Length: 0`) e a informação inteira vem em
    cabeçalhos `X-Goog-*`. É por isso que `TradutorDeEvento.traduzir` recebe os
    dois, e não só um deles.

    Uma notificação do Drive descreve uma mudança só, então a sequência devolvida
    tem sempre um elemento. Ela existe para satisfazer a porta, que precisa
    acomodar o lote do Graph.
    """

    def traduzir(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> Sequence[EventoWebhook]:
        cabecalho = _cabecalhos_normalizados(cabecalhos)

        canal = cabecalho.get("x-goog-channel-id")
        numero = cabecalho.get("x-goog-message-number")
        estado = cabecalho.get("x-goog-resource-state")

        # Sem canal e número não há chave de idempotência (TI-37); sem estado não
        # há como decidir se o evento é processável (TI-40).
        if not canal or not numero or not estado:
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO)

        return [
            EventoWebhook(
                identificador=f"{canal}:{numero}",
                tipo=f"drive.{estado}",
                versao=VERSAO_ENVELOPE,
                marca_de_tempo=datetime.now(UTC),
                correlacao=canal,
                conteudo={
                    "provedor": PROVEDOR,
                    "channel_id": canal,
                    "message_number": numero,
                    "resource_state": estado,
                    "resource_id": cabecalho.get("x-goog-resource-id"),
                    "resource_uri": cabecalho.get("x-goog-resource-uri"),
                    "changed": cabecalho.get("x-goog-changed"),
                },
            )
        ]


@dataclass(frozen=True)
class VerificadorChannelToken:
    """Confere o segredo que a aplicação definiu ao abrir o canal.

    É o equivalente exato do `clientState` do Microsoft Graph: um valor
    arbitrário informado no `changes.watch` e devolvido pelo provedor em toda
    notificação, no cabeçalho `X-Goog-Channel-Token`. Cobre as mesmas duas causas
    do TI-36 — ausência e divergência — e tem a mesma limitação: é constante ao
    longo da vida do canal, então não distingue entrega recente de entrega antiga.
    Por isso é composto com `VerificadorCanalAtivo`.
    """

    esperado: str

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        recebido = _cabecalhos_normalizados(cabecalhos).get("x-goog-channel-token")

        if recebido is None:
            raise WebhookError(WebhookErrorCode.ASSINATURA_AUSENTE)

        if not hmac.compare_digest(recebido, self.esperado):
            raise WebhookError(WebhookErrorCode.ASSINATURA_INVALIDA)


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class VerificadorCanalAtivo:
    """Recusa entregas de canais que já não valem mais.

    Mesma função de `VerificadorAssinaturaAtiva` no adaptador do Graph, e mesma
    justificativa: o Drive também não assina a notificação nem carimba a hora
    dela. O que ele oferece são o `X-Goog-Channel-ID`, confrontado com os canais
    ativos em `integracao.conexao`, e o `X-Goog-Channel-Expiration`, que recusa a
    entrega de um canal vencido.

    O cabeçalho de expiração vem em formato de data HTTP (RFC 2822), como
    `Tue, 19 Nov 2024 21:00:00 GMT`, e não em ISO 8601 — o Graph usa ISO. A
    tolerância a ambos abaixo existe porque a documentação do Google descreve o
    campo apenas como "human-readable", sem fixar o formato.
    """

    conexoes: RegistroConexoes
    agora: Callable[[], datetime] = field(default=_agora)

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        cabecalho = _cabecalhos_normalizados(cabecalhos)

        canal = cabecalho.get("x-goog-channel-id")
        if not canal:
            # Sem canal não há o que confrontar. Deixa passar de propósito, para o
            # tradutor recusar com 400: a entrega é inválida por estrutura, não por
            # autenticidade.
            return

        if not self.conexoes.assinatura_ativa(canal):
            raise WebhookError(WebhookErrorCode.ASSINATURA_EXPIRADA)

        expira_em = cabecalho.get("x-goog-channel-expiration")
        if expira_em and self._vencido(expira_em) < self.agora():
            raise WebhookError(WebhookErrorCode.ASSINATURA_EXPIRADA)

    def _vencido(self, expira_em: str) -> datetime:
        for interpretar in (parsedate_to_datetime, datetime.fromisoformat):
            try:
                instante = interpretar(expira_em)
            except (TypeError, ValueError):
                continue
            # Data HTTP sem fuso é UTC por definição; comparar ingênuo com
            # consciente levanta TypeError na hora errada.
            return instante if instante.tzinfo else instante.replace(tzinfo=UTC)

        raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO)
