"""Publicação de envelopes no barramento.

O `Publicador` é a porta que o produtor usa; há duas implementações. A real
(`PublicadorRabbitMQ`) declara a topologia de forma idempotente e publica com
confirmação do broker (publisher confirms) — se o broker estiver fora, ou
recusar (nack), a publicação LEVANTA, para que a falha suba e o receptor
devolva 5xx (TI-46: sem perda silenciosa). A no-op (`PublicacaoDesligada`) é o
que roda sem `RABBITMQ_URL`: aceita e descarta, mantendo o comportamento da
Sprint 4.

`pika` é importado dentro dos métodos de `PublicadorRabbitMQ`, e não no topo do
módulo: assim uma instalação sem broker (que usa `PublicacaoDesligada`) não
precisa nem ter `pika` presente para importar este módulo.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from mensageria.config import MensageriaSettings
from mensageria.envelope import serializar
from services.webhook_service import EventoWebhook

logger = logging.getLogger(__name__)


class PublicacaoIndisponivel(RuntimeError):
    """O barramento não pôde aceitar a publicação (broker fora, ou nack).

    Sobe a partir de `PublicadorRabbitMQ.publicar` e é o que o produtor traduz
    em falha explícita ao provedor (TI-46). Nunca é engolida.
    """


class Publicador(Protocol):
    """Porta de publicação. Uma chamada por evento a publicar."""

    def publicar(self, evento: EventoWebhook) -> None: ...


class PublicacaoDesligada:
    """Publicador no-op, usado quando não há `RABBITMQ_URL`.

    Deixa o composto `ProcessadorComPublicacao` indistinguível do processador da
    Sprint 4: marca-se o delta e nada mais acontece. É o que mantém os 32 testes
    de contrato de webhook verdes numa instalação sem broker.
    """

    def publicar(self, evento: EventoWebhook) -> None:
        return None


class PublicadorRabbitMQ:
    """Publica no RabbitMQ com topologia idempotente e publisher confirms.

    A conexão é aberta sob demanda e reaproveitada; se cair, a próxima
    publicação reabre. `delivery_mode=2` marca a mensagem como persistente, para
    que ela sobreviva a um restart do broker — junto com a fila durável, é o que
    dá durabilidade à entrega.

    A confirmação do broker vem de `confirm_delivery()`: com ela ligada, o
    `basic_publish` do pika levanta `UnroutableError`/`NackError` se a mensagem
    não for aceita, em vez de retornar em silêncio. Qualquer falha — broker
    inacessível, canal derrubado, nack — é reembrulhada em
    `PublicacaoIndisponivel`.
    """

    def __init__(self, settings: MensageriaSettings) -> None:
        self._settings = settings
        self._conexao: Any | None = None
        self._canal: Any | None = None

    def _garantir_canal(self) -> Any:
        import pika

        if self._canal is not None and self._canal.is_open:
            return self._canal

        parametros = pika.URLParameters(self._settings.url)
        # Reconexão na abertura: se o broker ainda está subindo, tenta algumas
        # vezes antes de desistir, em vez de falhar na primeira recusa.
        parametros.connection_attempts = max(parametros.connection_attempts, 3)
        parametros.retry_delay = max(parametros.retry_delay, 2)

        self._conexao = pika.BlockingConnection(parametros)
        canal = self._conexao.channel()
        declarar_topologia(canal, self._settings)
        # Publisher confirms: sem isto, o publish é fire-and-forget e um broker
        # que descarta a mensagem não gera erro nenhum — o oposto do TI-46.
        canal.confirm_delivery()
        self._canal = canal
        return canal

    def publicar(self, evento: EventoWebhook) -> None:
        import pika

        try:
            canal = self._garantir_canal()
            canal.basic_publish(
                exchange=self._settings.exchange,
                routing_key=self._settings.routing_key,
                body=serializar(evento),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistente
                    content_type="application/json",
                    message_id=evento.identificador,
                ),
                mandatory=True,
            )
        except Exception as exc:
            # Uma conexão meio-morta não pode ser reaproveitada: descarta para
            # que a próxima publicação reabra do zero.
            self._descartar_conexao()
            raise PublicacaoIndisponivel(
                f"falha ao publicar no barramento: {exc}"
            ) from exc

    def _descartar_conexao(self) -> None:
        for recurso in (self._canal, self._conexao):
            try:
                if recurso is not None and recurso.is_open:
                    recurso.close()
            except Exception:
                logger.debug("Falha ao fechar recurso do RabbitMQ; ignorando.", exc_info=True)
        self._canal = None
        self._conexao = None

    def fechar(self) -> None:
        self._descartar_conexao()


def declarar_topologia(canal: Any, settings: MensageriaSettings) -> None:
    """Declara exchange, fila, DLX e fila morta de forma idempotente.

    Chamada tanto pelo produtor quanto pelo consumidor na abertura: as
    declarações do AMQP são idempotentes desde que os argumentos coincidam, e
    ambos usam este mesmo código, então não há como divergirem.

    A fila principal é uma QUORUM QUEUE com `x-delivery-limit`. As duas escolhas
    andam juntas: só a quorum queue conta reentregas e aplica um limite de
    entregas de forma nativa. É esse limite que fecha o laço do TI-43 — uma
    mensagem cujo processamento reprova sempre é devolvida à fila
    (basic_nack requeue=True) e reentregue, com o contador subindo a cada volta;
    ao ultrapassar `x-delivery-limit`, o próprio broker a dead-letter-a para a
    DLX, sem o consumidor precisar contar tentativas na mão. Um payload
    indesserializável, por outro lado, é recusado com requeue=False pelo
    consumidor e vai para a DLX de imediato, sem consumir tentativas.

    `x-delivery-limit` é o total de ENTREGAS toleradas; para permitir
    `max_tentativas` processamentos antes de morrer, o limite é `max_tentativas`
    (a entrega além dele é a que dispara a dead-letter).
    """
    canal.exchange_declare(
        exchange=settings.exchange, exchange_type="direct", durable=True
    )
    canal.exchange_declare(exchange=settings.dlx, exchange_type="direct", durable=True)
    canal.queue_declare(
        queue=settings.fila_morta,
        durable=True,
        arguments={"x-queue-type": "quorum"},
    )
    canal.queue_bind(
        queue=settings.fila_morta,
        exchange=settings.dlx,
        routing_key=settings.routing_key,
    )
    canal.queue_declare(
        queue=settings.fila,
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": settings.dlx,
            "x-dead-letter-routing-key": settings.routing_key,
            "x-delivery-limit": settings.max_tentativas,
        },
    )
    canal.queue_bind(
        queue=settings.fila,
        exchange=settings.exchange,
        routing_key=settings.routing_key,
    )
