"""Processador que compõe o efeito de domínio com a publicação no barramento.

É a peça que torna a publicação ADITIVA: envolve o `ProcessadorEvento` da
Sprint 4 (o `ProcessadorVarreduraPendente`, que marca `delta_pendente = TRUE`)
e, depois dele, publica o mesmo envelope no barramento. Nada na rota, no serviço
`ReceberEventoWebhook` ou no banco muda — troca-se uma implementação de
`ProcessadorEvento` por outra, exatamente como a Seção 6.4 previu.

A ordem — marcar o delta ANTES de publicar — não é acidental. Se a marcação
falha (a origem foi desativada no meio do processamento), o interno já levanta
`WebhookError` e nem se chega a publicar. Se a publicação falha, o delta ficou
marcado (estado seguro: o próximo webhook, ou uma varredura manual, ainda o vê)
e a falha vira `WebhookError(FALHA_DE_PROCESSAMENTO)`, que faz `_receber_um`
liberar a reivindicação e devolver 503 — o provedor reentrega, e a idempotência
do TI-37 impede efeito duplo. É isto que satisfaz o TI-46 (nenhuma perda
silenciosa) sem violar o TI-38.
"""

from __future__ import annotations

from mensageria.publicador import PublicacaoIndisponivel, Publicador
from services.webhook_service import (
    EventoWebhook,
    ProcessadorEvento,
    WebhookError,
    WebhookErrorCode,
)


class ProcessadorComPublicacao:
    """`ProcessadorEvento` que marca o delta e publica no barramento.

    Implementa a mesma porta que o `ReceberEventoWebhook` já consome, então
    entra no lugar do processador atual sem tocar em mais nada.
    """

    def __init__(self, interno: ProcessadorEvento, publicador: Publicador) -> None:
        self._interno = interno
        self._publicador = publicador

    def suporta(self, tipo: str) -> bool:
        # Delegação pura: quem decide o que é processável continua sendo o
        # processador de domínio. Publicar não é responsabilidade deste método —
        # `_receber_um` chama `suporta` antes de `processar`, e publicar aqui
        # duplicaria a mensagem de eventos ignorados.
        return self._interno.suporta(tipo)

    def processar(self, evento: EventoWebhook) -> None:
        # (a) Efeito de domínio primeiro. Se a origem sumiu no meio, o interno
        # levanta WebhookError e a publicação nem acontece.
        self._interno.processar(evento)

        # (b) Publicação depois. Se o barramento está fora, converte em
        # FALHA_DE_PROCESSAMENTO para que `_receber_um` libere a reivindicação
        # (503 → reentrega), em vez de deixar a mensagem se perder.
        try:
            self._publicador.publicar(evento)
        except PublicacaoIndisponivel as exc:
            raise WebhookError(WebhookErrorCode.FALHA_DE_PROCESSAMENTO) from exc
