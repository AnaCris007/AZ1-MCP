from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from psycopg.types.json import Jsonb

from services.webhook_service import (
    EventoWebhook,
    SituacaoEvento,
    WebhookError,
    WebhookErrorCode,
)

# Como a situação é gravada no banco. `duplicado` não aparece aqui de propósito:
# uma entrega repetida não gera linha nova, ela encontra a que já existe.
_SITUACAO_NO_BANCO = {
    SituacaoEvento.PROCESSADO: "processado",
    SituacaoEvento.IGNORADO: "ignorado",
}


@dataclass(frozen=True)
class PostgresSettings:
    dsn: str

    @classmethod
    def from_environment(cls) -> PostgresSettings:
        return cls(dsn=os.environ.get("DATABASE_URL", "postgresql://az1:az1@localhost:5432/az1"))


def _partes(evento: EventoWebhook) -> tuple[str, str]:
    """Separa o identificador do envelope nas duas colunas do banco.

    O identificador canônico é `<origem>:<item>` — assinatura e item no Graph,
    canal e número da mensagem no Drive. O banco guarda os dois separados porque
    é sobre eles que a unicidade é declarada, e é ela que dá a idempotência.
    """
    origem, _, item = evento.identificador.partition(":")
    return origem, item


class RegistroEventosPostgres:
    """Grava a trilha de entregas em `auditoria.evento_webhook`.

    A idempotência do caso TI-37 não é implementada aqui: ela é uma propriedade
    do esquema, a restrição `UNIQUE (provedor, subscription_id, notificacao_id)`.
    Este adaptador apenas consulta o resultado do `ON CONFLICT` para saber se a
    entrega era inédita. Deixar a garantia no banco é o que a torna válida também
    quando duas réplicas da API recebem a mesma reentrega ao mesmo tempo — uma
    verificação em Python, feita antes do INSERT, perderia essa corrida.
    """

    def __init__(self, pool: Any, provedor: str) -> None:
        self._pool = pool
        self._provedor = provedor

    def registrar(self, evento: EventoWebhook) -> bool:
        origem, item = _partes(evento)

        with self._pool.connection() as conexao:
            inserida = conexao.execute(
                """
                INSERT INTO auditoria.evento_webhook
                    (provedor, subscription_id, notificacao_id, tipo, versao_envelope,
                     correlacao, conteudo, recebido_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (provedor, subscription_id, notificacao_id) DO NOTHING
                RETURNING id
                """,
                (
                    self._provedor,
                    origem,
                    item,
                    evento.tipo,
                    evento.versao,
                    evento.correlacao,
                    Jsonb(dict(evento.conteudo)),
                    evento.marca_de_tempo,
                ),
            ).fetchone()

            if inserida is not None:
                return True

            # A linha já existia. Ela só é duplicata de fato se tiver concluído:
            # uma entrega registrada mas interrompida por falha (caso TI-38) tem
            # `concluido_em` nulo, e a reentrega precisa poder retomá-la.
            linha = conexao.execute(
                """
                SELECT concluido_em FROM auditoria.evento_webhook
                 WHERE provedor = %s AND subscription_id = %s AND notificacao_id = %s
                """,
                (self._provedor, origem, item),
            ).fetchone()

        return linha is not None and linha[0] is None

    def marcar_processado(self, evento: EventoWebhook, situacao: SituacaoEvento) -> None:
        origem, item = _partes(evento)

        with self._pool.connection() as conexao:
            conexao.execute(
                """
                UPDATE auditoria.evento_webhook
                   SET concluido_em = now(), situacao = %s
                 WHERE provedor = %s AND subscription_id = %s AND notificacao_id = %s
                """,
                (_SITUACAO_NO_BANCO[situacao], self._provedor, origem, item),
            )

    def registrar_recusa(self, *, motivo: str, corpo: bytes) -> None:
        # A entrega provou vir do provedor mas não pôde ser interpretada (TI-39).
        # Vai para a mesma tabela, sem envelope, para preservar uma ordem única do
        # que o provedor enviou — é o que a auditoria precisa responder.
        with self._pool.connection() as conexao:
            conexao.execute(
                """
                INSERT INTO auditoria.evento_webhook (provedor, corpo_bruto, motivo, situacao)
                VALUES (%s, %s, %s, 'recusado')
                """,
                (self._provedor, corpo.decode("utf-8", errors="replace"), motivo),
            )


class RegistroConexoesPostgres:
    """Responde se uma assinatura (Graph) ou canal (Drive) ainda vale."""

    def __init__(self, pool: Any, provedor: str) -> None:
        self._pool = pool
        self._provedor = provedor

    def assinatura_ativa(self, subscription_id: str) -> bool:
        with self._pool.connection() as conexao:
            linha = conexao.execute(
                """
                SELECT 1 FROM integracao.conexao
                 WHERE provedor = %s AND subscription_id = %s AND ativa
                   AND (expira_em IS NULL OR expira_em > now())
                """,
                (self._provedor, subscription_id),
            ).fetchone()

        return linha is not None


class ProcessadorVarreduraPendente:
    """Marca a origem como pendente de varredura.

    Este é o efeito de domínio da Sprint 4, e ele é pequeno de propósito. Nem o
    Graph nem o Drive dizem *o que* mudou: os dois dizem apenas que algo mudou na
    origem observada, e descobrir o quê exige uma chamada posterior (`delta` num,
    `changes.list` no outro), seguida de download, extração de texto e
    vetorização. Nada disso cabe na janela de poucos segundos que os provedores
    concedem antes de considerar a entrega falha.

    Por isso o receptor confirma com 202 e para aqui. A varredura é trabalho do
    consumidor do barramento da Sprint 5, e `integracao.conexao.delta_pendente` é
    a marca que ele vai ler. Trocar esta implementação por outra que publique numa
    fila é trocar uma classe, sem tocar em rota, serviço ou banco.
    """

    def __init__(self, pool: Any, provedor: str, tipos_suportados: frozenset[str]) -> None:
        self._pool = pool
        self._provedor = provedor
        self._tipos_suportados = tipos_suportados

    def suporta(self, tipo: str) -> bool:
        return tipo in self._tipos_suportados

    def processar(self, evento: EventoWebhook) -> None:
        with self._pool.connection() as conexao:
            atualizada = conexao.execute(
                """
                UPDATE integracao.conexao
                   SET delta_pendente = TRUE
                 WHERE provedor = %s AND subscription_id = %s AND ativa
                RETURNING id
                """,
                (self._provedor, evento.correlacao),
            ).fetchone()

        if atualizada is None:
            # O verificador já confirmou que a origem estava ativa; chegar aqui sem
            # linha significa que ela foi desativada no meio do processamento.
            # Devolver 5xx faz o provedor reentregar, e aí a recusa acontece na
            # verificação, que é onde ela pertence.
            raise WebhookError(WebhookErrorCode.FALHA_DE_PROCESSAMENTO)
