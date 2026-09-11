from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

DEFAULT_PERFIL = "lider_projeto"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainUser:
    id: int
    perfil: str


class Cursor(Protocol):
    def execute(self, query: str, params: tuple = ()) -> None: ...
    def fetchone(self) -> tuple | None: ...
    def __enter__(self) -> Cursor: ...
    def __exit__(self, *exc: object) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...
    def __enter__(self) -> Connection: ...
    def __exit__(self, *exc: object) -> None: ...


class ConnectionPool(Protocol):
    def connection(self) -> Connection: ...


class ResolveOrCreateUsuario:
    """Liga a identidade autenticada (Supabase Auth) a um registro de
    `portfolio.usuario`, criando um novo se nenhum bater por `auth_user_id` nem
    e-mail. É o gancho que `src/database/03_rls_policies.sql` já espera: a
    função `portfolio.usuario_atual()` só devolve algo diferente de NULL depois
    que `auth_user_id` estiver preenchido (ver `src/database/README.md`,
    "Ganchos para a autenticação").

    Pessoas reais não batem com os 10 usuários sintéticos seedados em
    `02_initial_data.sql` (e-mails `@metro.example`) — por isso, no primeiro
    login sem correspondência, um registro novo é criado com `perfil`
    padrão. É uma decisão deliberada, não um valor arbitrário: o RNF02 não
    estabelece autorização por cargo (Seção 2.3), então nenhuma funcionalidade
    muda de comportamento em função de qual dos três perfis a pessoa recebe.
    """

    def __init__(self, pool: ConnectionPool, default_perfil: str = DEFAULT_PERFIL) -> None:
        self._pool = pool
        self._default_perfil = default_perfil

    def resolve(self, *, auth_user_id: str, email: str, name: str) -> DomainUser:
        email_normalizado = email.strip().lower()
        nome = name.strip() if name and name.strip() else email_normalizado

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, perfil FROM portfolio.usuario WHERE auth_user_id = %s AND ativo",
                (auth_user_id,),
            )
            row = cur.fetchone()
            if row is not None:
                return DomainUser(id=row[0], perfil=row[1])

            cur.execute(
                "SELECT id, perfil FROM portfolio.usuario "
                "WHERE lower(email) = %s AND auth_user_id IS NULL AND ativo",
                (email_normalizado,),
            )
            row = cur.fetchone()
            if row is not None:
                usuario_id, perfil = row
                cur.execute(
                    "UPDATE portfolio.usuario SET auth_user_id = %s WHERE id = %s",
                    (auth_user_id, usuario_id),
                )
                conn.commit()
                logger.info("Ligado portfolio.usuario.id=%s ao login de %s", usuario_id, email_normalizado)
                return DomainUser(id=usuario_id, perfil=perfil)

            cur.execute(
                "INSERT INTO portfolio.usuario (auth_user_id, nome, email, perfil) "
                "VALUES (%s, %s, %s, %s) RETURNING id, perfil",
                (auth_user_id, nome, email_normalizado, self._default_perfil),
            )
            row = cur.fetchone()
            assert row is not None
            conn.commit()
            logger.info("Criado portfolio.usuario.id=%s para o login de %s", row[0], email_normalizado)
            return DomainUser(id=row[0], perfil=row[1])
