from __future__ import annotations

import os
from functools import lru_cache

import sqlalchemy


@lru_cache(maxsize=1)
def obter_engine() -> sqlalchemy.Engine:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL não configurada")
    return sqlalchemy.create_engine(url, pool_pre_ping=True)
