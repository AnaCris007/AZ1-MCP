"""Configuração do barramento: URL do broker e nomes de topologia.

Os nomes de exchange, fila, routing key e da dead-letter ficam aqui, num só
lugar, porque produtor e consumidor precisam concordar sobre eles ao pé da
letra — uma divergência de uma letra faz a mensagem ser publicada numa fila que
ninguém consome, sem erro nenhum. Centralizar é o que impede essa divergência.

`from_environment` devolve `None` quando `RABBITMQ_URL` está ausente: é o
sinal de que a publicação deve degradar para no-op (graceful degradation),
mantendo o comportamento da Sprint 4 intacto numa instalação sem broker.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Número de entregas que uma mensagem sofre antes de ser dada por irrecuperável.
# É o default de `max_tentativas` e o fallback quando `RABBITMQ_MAX_TENTATIVAS`
# está ausente ou mal formado.
_MAX_TENTATIVAS_PADRAO = 3


def _max_tentativas_do_ambiente() -> int:
    """Lê `RABBITMQ_MAX_TENTATIVAS` (int); cai no default se ausente/inválido."""
    bruto = os.environ.get("RABBITMQ_MAX_TENTATIVAS", "").strip()
    if not bruto:
        return _MAX_TENTATIVAS_PADRAO
    try:
        return int(bruto)
    except ValueError:
        return _MAX_TENTATIVAS_PADRAO


@dataclass(frozen=True)
class MensageriaSettings:
    """Endereço do broker e a topologia que produtor e consumidor compartilham.

    Os padrões descrevem a topologia da Seção 6.4.4: uma exchange `direct`
    durável, uma fila durável ligada a ela pela routing key, e uma
    dead-letter-exchange com sua própria fila morta para onde vão as mensagens
    que o consumidor recusa em definitivo. `max_tentativas` é o número de
    entregas que uma mensagem sofre antes de ser considerada irrecuperável.
    """

    url: str
    exchange: str = "az1.eventos"
    routing_key: str = "varredura"
    fila: str = "varredura.pendente"
    dlx: str = "az1.eventos.dlx"
    fila_morta: str = "varredura.morta"
    max_tentativas: int = _MAX_TENTATIVAS_PADRAO

    @classmethod
    def from_environment(cls) -> MensageriaSettings | None:
        """Lê `RABBITMQ_URL`; devolve `None` se ausente ou vazia.

        O `None` é deliberado e não um erro: sem broker, o sistema deve seguir
        funcionando como na Sprint 4. Quem chama decide o que fazer com a
        ausência — `get_publicador` a traduz em `PublicacaoDesligada`.

        `max_tentativas` sai de `RABBITMQ_MAX_TENTATIVAS` (int); valor ausente ou
        inválido cai no default 3, para não derrubar a inicialização por causa de
        um env mal digitado.
        """
        url = os.environ.get("RABBITMQ_URL", "").strip()
        if not url:
            return None
        return cls(url=url, max_tentativas=_max_tentativas_do_ambiente())
