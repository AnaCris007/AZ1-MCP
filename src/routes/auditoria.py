from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from az1_api.dependencies import get_listador_auditoria, require_authenticated_user
from schemas.auditoria import AuditoriaErrorCode, AuditoriaListResponse, ConsultaLog
from services.auditoria_service import ListarConsultas
from services.auth_service import AuthenticatedUser

router = APIRouter(tags=["auditoria"])

# `03_rls_policies.sql` define a regra de acesso do RNF02: autenticação sim,
# autorização por cargo não — EXCETO a conversa, que é de cada um, e cuja
# leitura administrativa é justamente esta rota. Ela devolve `conteudo` de
# `auditoria.mensagem` sem filtro de dono, o que é correto para auditoria e
# seria vazamento para qualquer outro. Daí o perfil.
PERFIS_ADMINISTRATIVOS = frozenset({"diretor", "pmo"})


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
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuditoriaListResponse:
    # Perfil ausente (banco fora do ar, ligação com portfolio.usuario falhou)
    # não é administrador. A dúvida recusa: esta rota entrega conversa alheia.
    if usuario.perfil not in PERFIS_ADMINISTRATIVOS:
        raise AuditoriaAPIError(
            403,
            "forbidden",
            "A trilha de auditoria é restrita aos perfis diretor e PMO.",
        )

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
