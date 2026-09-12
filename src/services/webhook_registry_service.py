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
# repetir um identificador estável encontra a linha existente. Avisos mínimos
# OneDrive usam UUID novo e são registrados como novos recebimentos.
_SITUACAO_NO_BANCO = {
    SituacaoEvento.PROCESSADO: "processado",
    SituacaoEvento.IGNORADO: "ignorado",
}


@dataclass(frozen=True)
class PostgresSettings:
    dsn: str

    @classmethod
    def from_environment(cls) -> PostgresSettings:
        return cls(dsn=(os.environ.get("DATABASE_URL", "").strip()
                        or os.environ.get("SUPABASE_DB_URL", "").strip()
                        or "postgresql://az1:az1@localhost:5432/az1"))


def _partes(evento: EventoWebhook) -> tuple[str, str]:
    """Separa o identificador do envelope nas duas colunas do banco.

    O identificador canônico é `<origem>:<evento-ou-recebimento>`. Graph usa
    identidade de evento/versão quando disponível, ou UUID por recebimento;
    Drive usa canal e número da mensagem. O UNIQUE só deduplica identidades
    estáveis, não os UUIDs distintos de avisos mínimos OneDrive.
    """
    origem, _, item = evento.identificador.partition(":")
    return origem, item


class _ReivindicacaoPostgres:
    """Uma conexão retirada do pool sem devolução automática, segurada aberta
    entre `reivindicar` e `concluir`/`liberar`.

    É essa conexão — mais precisamente, o lock de linha que ela detém desde o
    INSERT ou o `SELECT ... FOR UPDATE` que a criou — que serializa duas
    reivindicações concorrentes do mesmo evento. Nenhum dos dois métodos abaixo
    pode deixar de devolvê-la ao pool, daí o `finally` nos dois.
    """

    def __init__(self, pool: Any, conexao: Any, provedor: str, origem: str, item: str) -> None:
        self._pool = pool
        self._conexao = conexao
        self._provedor = provedor
        self._origem = origem
        self._item = item

    def concluir(self, situacao: SituacaoEvento) -> None:
        try:
            self._conexao.execute(
                """
                UPDATE auditoria.evento_webhook
                   SET concluido_em = now(), situacao = %s
                 WHERE provedor = %s AND subscription_id = %s AND notificacao_id = %s
                """,
                (_SITUACAO_NO_BANCO[situacao], self._provedor, self._origem, self._item),
            )
            self._conexao.commit()
        finally:
            self._pool.putconn(self._conexao)

    def liberar(self) -> None:
        # Sem tocar em concluido_em, e com commit — não rollback: um rollback
        # desfaria o INSERT desta tentativa (se foi ela quem inseriu a linha),
        # fazendo o evento desaparecer da auditoria sem deixar rastro de que
        # chegou. O commit preserva a linha, ainda pendente, e libera o lock
        # para a próxima tentativa — reentrega do provedor (TI-38) ou uma
        # segunda entrega concorrente que estava esperando nesta mesma chamada.
        try:
            self._conexao.commit()
        finally:
            self._pool.putconn(self._conexao)


class RegistroEventosPostgres:
    """Grava a trilha de entregas em `auditoria.evento_webhook`.

    Para identificadores estáveis, a deduplicação do TI-37 e a retomada do TI-38 são a
    mesma exclusividade, vista em dois desfechos — não dois mecanismos
    separados. `reivindicar` tenta o INSERT; se a linha já existe, trava-a com
    `SELECT ... FOR UPDATE` e esse `SELECT` *bloqueia* caso outra transação já
    esteja segurando essa mesma linha, em vez de decidir com base numa leitura
    que pode estar desatualizada. Só depois de destravar — quando a outra
    transação já concluiu ou liberou — é que este método decide se ainda há o
    que fazer. Uma versão anterior deste método usava uma janela de tempo para
    essa decisão em vez de um lock; falhava exatamente no caso TI-38, porque
    não existe prazo que distinga de forma confiável "outra entrega deste
    mesmo evento está processando agora" de "a tentativa anterior falhou e o
    provedor está reentregando rápido" — as duas acontecem na mesma escala de
    tempo. Um lock de banco resolve os dois casos com a mesma regra, sem
    precisar adivinhar quanto tempo é "rápido demais".
    """

    def __init__(self, pool: Any, provedor: str) -> None:
        self._pool = pool
        self._provedor = provedor

    def reivindicar(self, evento: EventoWebhook) -> _ReivindicacaoPostgres | None:
        origem, item = _partes(evento)
        conexao = self._pool.getconn()

        transferida = False
        try:
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
                transferida = True
                return _ReivindicacaoPostgres(self._pool, conexao, self._provedor, origem, item)

            # A linha já existia: FOR UPDATE trava-a, bloqueando aqui mesmo se
            # outra transação a estiver segurando neste instante. Ao desbloquear —
            # depois que a outra concluir ou liberar —, o estado já é definitivo.
            linha = conexao.execute(
                """
                SELECT concluido_em FROM auditoria.evento_webhook
                 WHERE provedor = %s AND subscription_id = %s AND notificacao_id = %s
                 FOR UPDATE
                """,
                (self._provedor, origem, item),
            ).fetchone()

            if linha is not None and linha[0] is None:
                transferida = True
                return _ReivindicacaoPostgres(self._pool, conexao, self._provedor, origem, item)

            # Concluída por outra tentativa: duplicata de verdade (TI-37).
            conexao.commit()
            return None
        except BaseException:
            try:
                conexao.rollback()
            except Exception:
                conexao.close()
            raise
        finally:
            if not transferida:
                self._pool.putconn(conexao)

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
