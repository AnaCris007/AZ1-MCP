"""Os quatro modos de operação da fita.

A tabela da Seção 6.4.3 define as modalidades pelo nome do modo do VCR.py.
Este enum é o adaptador entre o vocabulário do plano (`gravar`, `reproduzir`,
`atualizar`, `desligado`) e o da biblioteca (`once`, `none`, `all`, e a ausência
de contexto). Ele não é lido de variável de ambiente: a Seção 6.4.3 registra
explicitamente que `VHS_MODO` não existe, e o modo é escolhido em código, por
quem monta a suíte.
"""

from __future__ import annotations

from enum import Enum


class Modo(Enum):
    """Modalidade de uso da fita, conforme a tabela da Seção 6.4.3."""

    GRAVAR = "gravar"
    REPRODUZIR = "reproduzir"
    ATUALIZAR = "atualizar"
    DESLIGADO = "desligado"

    @property
    def record_mode(self) -> str | None:
        """Modo correspondente do VCR.py, ou `None` quando não há contexto."""
        return {
            Modo.GRAVAR: "once",
            Modo.REPRODUZIR: "none",
            Modo.ATUALIZAR: "all",
            Modo.DESLIGADO: None,
        }[self]

    @property
    def abre_contexto(self) -> bool:
        """Se este modo abre um contexto VCR.

        Em `desligado` não se lê nem se grava nada: a chamada vai ao serviço
        real, que é o uso de smoke de contrato e de medição de desempenho.
        """
        return self is not Modo.DESLIGADO

    @property
    def permite_rede(self) -> bool:
        """Se a rede pode ser usada neste modo.

        Só `reproduzir` promete ausência de saída para a rede. Os demais ou
        gravam uma interação real, ou não interceptam coisa alguma.
        """
        return self is not Modo.REPRODUZIR
