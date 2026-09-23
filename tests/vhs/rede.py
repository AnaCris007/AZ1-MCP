"""Bloqueio e contagem de saídas para a rede.

A tabela da Seção 6.4.3 descreve o modo de replay como "rede bloqueada no
executor", e TI-49 exige que a falha por registro ausente ocorra **sem nenhuma
requisição**. Sem um bloqueio armado, "nenhuma chamada nova" é uma afirmação
sobre o que se espera do VCR.py, não sobre o que aconteceu.

O item 4 do contrato acrescenta a outra metade: `cassette.play_count` mede
replay, e não substitui um contador externo de chamadas reais. Por isso este
módulo oferece as duas ferramentas — o bloqueio, que impede, e o contador, que
observa sem impedir — e as duas atuam na mesma altura: a chamada de `connect`
do socket, abaixo de qualquer interceptação do VCR.py e de qualquer SDK.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from unittest.mock import patch

from tests.vhs.erros import RedeBloqueada


@dataclass
class ContadorDeRede:
    """Tentativas de conexão observadas enquanto o contexto esteve aberto."""

    tentativas: int = 0
    destinos: list[str] = field(default_factory=list)

    def anotar(self, destino: object) -> None:
        self.tentativas += 1
        self.destinos.append(str(destino))


@contextmanager
def rede_bloqueada() -> Iterator[ContadorDeRede]:
    """Faz qualquer tentativa de conexão levantar `RedeBloqueada`.

    O bloqueio é só do lado cliente: `connect`, `connect_ex` e
    `create_connection`. Um servidor local de teste continua aceitando conexões
    — o que se quer provar é que o código sob teste não saiu, não que a máquina
    ficou muda.
    """
    contador = ContadorDeRede()

    def recusar(_eu: object, endereco: object, *_resto: object, **_nomeados: object):
        contador.anotar(endereco)
        raise RedeBloqueada(f"conexão para {endereco} durante replay: a fita deveria bastar")

    def recusar_direto(endereco: object, *_resto: object, **_nomeados: object):
        contador.anotar(endereco)
        raise RedeBloqueada(f"conexão para {endereco} durante replay: a fita deveria bastar")

    with (
        patch.object(socket.socket, "connect", recusar),
        patch.object(socket.socket, "connect_ex", recusar),
        patch.object(socket, "create_connection", recusar_direto),
    ):
        yield contador


@contextmanager
def contador_de_conexoes() -> Iterator[ContadorDeRede]:
    """Conta conexões sem impedi-las, para a evidência da sessão de gravação."""
    contador = ContadorDeRede()
    original = socket.socket.connect

    def observar(eu: socket.socket, endereco: object, *resto: object, **nomeados: object):
        contador.anotar(endereco)
        return original(eu, endereco, *resto, **nomeados)

    with patch.object(socket.socket, "connect", observar):
        yield contador
