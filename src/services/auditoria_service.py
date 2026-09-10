from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy
from sqlalchemy import text

logger = logging.getLogger(__name__)

_USUARIO_SISTEMA = 0


@dataclass(frozen=True)
class MensagemRegistrada:
    id: str
    conversa_id: str
    papel: str
    conteudo: str
    tempo_processamento_ms: int | None
    criada_em: str


class GravarConsulta:
    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine

    def gravar(
        self,
        *,
        mensagem: str,
        resposta: str | None,
        conversation_id: str | None,
        duracao_ms: int | None,
    ) -> None:
        if not conversation_id:
            return

        try:
            conversa_uuid = str(uuid.UUID(conversation_id))
        except ValueError:
            logger.warning("conversation_id '%s' não é UUID válido — auditoria ignorada", conversation_id)
            return

        try:
            with self._engine.connect() as conn:
                conn.execute(
                    text(
                        "INSERT INTO auditoria.conversa (id, usuario_id) "
                        "VALUES (:id, :uid) ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": conversa_uuid, "uid": _USUARIO_SISTEMA},
                )

                row = conn.execute(
                    text(
                        "SELECT COALESCE(MAX(ordem), 0) AS max_ordem "
                        "FROM auditoria.mensagem WHERE conversa_id = :id"
                    ),
                    {"id": conversa_uuid},
                ).one()
                proxima = row.max_ordem + 1

                conn.execute(
                    text(
                        "INSERT INTO auditoria.mensagem "
                        "(conversa_id, ordem, papel, formato, conteudo) "
                        "VALUES (:cid, :ordem, 'usuario', 'texto', :conteudo)"
                    ),
                    {"cid": conversa_uuid, "ordem": proxima, "conteudo": mensagem},
                )

                if resposta is not None:
                    conn.execute(
                        text(
                            "INSERT INTO auditoria.mensagem "
                            "(conversa_id, ordem, papel, formato, conteudo, resultado, tempo_processamento_ms) "
                            "VALUES (:cid, :ordem, 'agente', 'texto', :conteudo, 'sucesso', :tempo)"
                        ),
                        {
                            "cid": conversa_uuid,
                            "ordem": proxima + 1,
                            "conteudo": resposta,
                            "tempo": duracao_ms,
                        },
                    )

                conn.commit()
        except Exception:
            logger.exception("Falha ao registrar auditoria para conversa %s", conversa_uuid)


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
