from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from az1_api.dependencies import get_listador_auditoria
from schemas.auditoria import AuditoriaErrorCode, AuditoriaListResponse, ConsultaLog
from services.auditoria_service import ListarConsultas

router = APIRouter(tags=["auditoria"])


class AuditoriaAPIError(Exception):
    def __init__(self, status_code: int, error: AuditoriaErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@router.get("/auditoria/consultas", response_model=AuditoriaListResponse, status_code=200)
def listar_consultas(
    limit: int = Query(default=50, ge=1, le=100, description="Número máximo de registros retornados."),
    desde: datetime | None = Query(default=None, description="Filtrar consultas a partir desta data (ISO 8601)."),
    listador: ListarConsultas = Depends(get_listador_auditoria),
) -> AuditoriaListResponse:
    registros = listador.listar(limit=limit, desde=desde)
    return AuditoriaListResponse(
        consultas=[
            ConsultaLog(
                id=r.id,
                conversa_id=r.conversa_id,
                papel=r.papel,
                conteudo=r.conteudo,
                tempo_processamento_ms=r.tempo_processamento_ms,
                criada_em=r.criada_em,
            )
            for r in registros
        ]
    )
