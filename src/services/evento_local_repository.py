# Compromissos próprios do usuário na Agenda.
#
# Arquivo à parte de `portfolio_repository.py` de propósito: aquele é
# somente-leitura sobre o domínio de portfólio (projeto, pendência); isto é
# dado de posse do usuário, com ciclo de vida próprio (cria, apaga), mesmo
# motivo que já separa `conversa_repository.py` de `portfolio_repository.py`.
#
# A aplicação conecta hoje como dono do schema (`AZ1_DB_ROLE` opcional, ver
# `database_service.py`): a RLS de `07_evento_local.sql` ainda não é aplicada.
# Por isso o filtro por `usuario_id` está explícito no SQL abaixo, e não só na
# política — mesma ressalva já documentada em
# `PortfolioRepository.alterar_situacao`.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from psycopg_pool import ConnectionPool


@dataclass(frozen=True)
class EventoLocal:
    id: int
    titulo: str
    data: date
    hora: time | None
    descricao: str


_SQL_LISTAR = """
SELECT id, titulo, data, hora, descricao
  FROM portfolio.evento_local
 WHERE usuario_id = %s
 ORDER BY data, hora NULLS FIRST
"""

_SQL_CRIAR = """
INSERT INTO portfolio.evento_local (usuario_id, titulo, data, hora, descricao)
VALUES (%s, %s, %s, %s, %s)
RETURNING id, titulo, data, hora, descricao
"""

_SQL_APAGAR = """
DELETE FROM portfolio.evento_local WHERE id = %s AND usuario_id = %s RETURNING id
"""


def _para_evento(linha: tuple) -> EventoLocal:
    return EventoLocal(
        id=linha[0],
        titulo=linha[1],
        data=linha[2],
        hora=linha[3],
        descricao=linha[4] or "",
    )


class EventoLocalRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def listar(self, usuario_id: int) -> tuple[EventoLocal, ...]:
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_LISTAR, (usuario_id,))
            return tuple(_para_evento(linha) for linha in cursor.fetchall())

    def criar(
        self, *, usuario_id: int, titulo: str, data: date, hora: time | None, descricao: str
    ) -> EventoLocal:
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_CRIAR, (usuario_id, titulo, data, hora, descricao))
            return _para_evento(cursor.fetchone())

    def apagar(self, *, usuario_id: int, evento_id: int) -> bool:
        """Apaga o evento se ele pertencer a `usuario_id`; devolve se apagou.

        O `usuario_id` no WHERE é a checagem de posse: uma tentativa de apagar
        o evento de outra pessoa devolve `False` (o chamador traduz para 404),
        não sucesso silencioso sobre a linha errada.
        """
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_APAGAR, (evento_id, usuario_id))
            return cursor.fetchone() is not None
