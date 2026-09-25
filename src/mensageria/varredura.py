"""Efeito de domínio do CONSUMIDOR: dar a origem por varrida.

O produtor marca `integracao.conexao.delta_pendente = TRUE`; este é o outro lado
do par, executado pelo worker: localiza a conexão por `correlacao` (o
subscription_id do Graph ou o canal do Drive) e marca `delta_pendente = FALSE`.

USA O MESMO PAPEL `az1_webhook` do receptor. A migração 06 já concede
`UPDATE (delta_pendente) ON integracao.conexao` a esse papel (linhas 47-48 de
`06_webhook_permissions.sql`), então o worker não exige migração nova.

Três pontos que a implementação assume, e que ficam registrados aqui de
propósito:

  (i) `delta_pendente` é um booleano-DE-NÍVEL, não um contador. Há uma corrida
      aceita para a PoC: o produtor marca TRUE a cada webhook de um burst e o
      consumidor marca FALSE ao varrer; a última mudança de um burst pode ficar
      não-varrida até o próximo webhook reacender a marca. Para a PoC isto é
      tolerável — a próxima notificação corrige. Um contador (ou um marcador com
      versão/etag) fecharia a janela, e é o caminho natural quando a
      reindexação real entrar.

  (ii) Este é o stub SÓ-DE-ESTADO: fecha `delta_pendente` sem baixar nem
       reindexar nada. Serve de FALLBACK quando faltam credenciais para a
       varredura real (ver `_indexacao_disponivel` em `mensageria.consumidor`).
       A reindexação REAL do Google Drive (delta feed → baixar → extrair →
       vetorizar → indexar no pgvector) JÁ EXISTE, em
       `mensageria.varredura_indexacao` (`VarreduraComIndexacao`), com a MESMA
       interface `varrer(evento)` — o consumidor troca uma pela outra sem mudar
       mais nada. Para o Microsoft Graph a reindexação continua não
       implementada: o tenant ao vivo está indisponível (Seção 5.1.1), então lá
       este stub segue sendo o único caminho.

  (iii) A operação é IDEMPOTENTE: reprocessar a mesma mensagem marca FALSE de
        novo, efeito único (base do TI-44). O `identificador` do envelope é
        aceito para o encaixe futuro poder deduplicar por identidade estável
        (registrar "já varri esta mudança") sem mudar a assinatura desta porta.
"""

from __future__ import annotations

import logging
from typing import Any

from services.webhook_service import EventoWebhook

logger = logging.getLogger(__name__)


class VarreduraDeConexao:
    """Marca a origem correlacionada como varrida (`delta_pendente = FALSE`)."""

    def __init__(self, pool: Any, provedor: str | None = None) -> None:
        self._pool = pool
        self._provedor = provedor

    def varrer(self, evento: EventoWebhook) -> None:
        """Fecha o ciclo de estado da origem apontada pela `correlacao`.

        O `identificador` (evento.identificador) fica disponível para o encaixe
        futuro deduplicar por identidade estável; hoje a marca de nível já é
        idempotente, então não é consultado.
        """
        with self._pool.connection() as conexao:
            atualizada = conexao.execute(
                """
                UPDATE integracao.conexao
                   SET delta_pendente = FALSE
                 WHERE subscription_id = %s AND ativa
                RETURNING id
                """,
                (evento.correlacao,),
            ).fetchone()

        if atualizada is None:
            # Não é erro do worker: a origem pode ter sido desativada entre a
            # publicação e o consumo. Loga e segue — reentregar não mudaria nada,
            # então o consumidor confirma (ack) a mensagem mesmo assim.
            logger.info(
                "Varredura sem origem ativa para correlacao=%s (identificador=%s); "
                "origem provavelmente desativada após a publicação.",
                evento.correlacao,
                evento.identificador,
            )
