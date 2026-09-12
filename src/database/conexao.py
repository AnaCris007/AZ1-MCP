from __future__ import annotations

import os
from functools import lru_cache

import sqlalchemy

# UMA definição só, reexportada — não uma classe própria com o mesmo nome.
#
# Este módulo declarava a sua, e `services/database_service.py` já declarava
# outra. Duas classes homônimas subindo a mesma pilha significam que
# `@app.exception_handler(BancoNaoConfigurado)` registra UMA delas: a que vier do
# outro módulo escapa e cai no manipulador genérico de 500 — sem erro de import,
# sem aviso, com a resposta errada.
#
# O `ruff` pega a redefinição dentro de um arquivo (F811), mas não entre
# arquivos. A reexportação é o que fecha essa porta.
from services.database_service import BancoNaoConfigurado  # noqa: F401

__all__ = ["BancoNaoConfigurado", "obter_engine"]


@lru_cache(maxsize=1)
def obter_engine() -> sqlalchemy.Engine:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        raise BancoNaoConfigurado(
            "SUPABASE_DB_URL não configurada. Use a connection string PostgreSQL do "
            "Supabase (Settings → Database → Connection string → URI)."
        )
    return sqlalchemy.create_engine(url, pool_pre_ping=True)
