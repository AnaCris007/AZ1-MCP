from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MensagemRegistrada:
    id: str
    conversa_id: str
    papel: str
    conteudo: str
    tempo_processamento_ms: int | None
    criada_em: str


class ListarConsultas:
    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine

    def listar(
        self,
        *,
        limit: int = 50,
        desde: datetime | None = None,
    ) -> list[MensagemRegistrada]:
        limit = min(limit, 100)
        if desde is not None:
            consulta = text(
                "SELECT id, conversa_id, papel, conteudo, tempo_processamento_ms, criada_em "
                "FROM auditoria.mensagem "
                "WHERE criada_em >= :desde "
                "ORDER BY criada_em DESC LIMIT :limit"
            )
            params: dict[str, object] = {"limit": limit, "desde": desde}
        else:
            consulta = text(
                "SELECT id, conversa_id, papel, conteudo, tempo_processamento_ms, criada_em "
                "FROM auditoria.mensagem "
                "ORDER BY criada_em DESC LIMIT :limit"
            )
            params = {"limit": limit}

        with self._engine.connect() as conn:
            rows = conn.execute(consulta, params).all()

        return [
            MensagemRegistrada(
                id=str(r.id),
                conversa_id=str(r.conversa_id),
                papel=r.papel,
                conteudo=r.conteudo,
                tempo_processamento_ms=r.tempo_processamento_ms,
                criada_em=r.criada_em.isoformat(),
            )
            for r in rows
        ]
