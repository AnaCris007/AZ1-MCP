from __future__ import annotations

import os
from functools import lru_cache

import sqlalchemy


class BancoNaoConfigurado(RuntimeError):
    """`SUPABASE_DB_URL` ausente ou vazia.

    Tipo próprio, e não `RuntimeError` cru, porque a distinção importa na
    borda HTTP: banco ausente é indisponibilidade de dependência (503), não
    erro de programação (500). Sem um tipo para reconhecer, o manipulador
    teria de capturar `RuntimeError` inteiro e engoliria defeitos de verdade.
    """


@lru_cache(maxsize=1)
def obter_engine() -> sqlalchemy.Engine:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        raise BancoNaoConfigurado(
            "SUPABASE_DB_URL não configurada. Use a connection string PostgreSQL do "
            "Supabase (Settings → Database → Connection string → URI)."
        )
    return sqlalchemy.create_engine(url, pool_pre_ping=True)
