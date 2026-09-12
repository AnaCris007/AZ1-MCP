from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends

from az1_api.dependencies import get_alerta_desativador, get_alerta_listador, get_alerta_registrador
from schemas.alerta import (
    AlertaErrorCode,
    AssinanteCreatedResponse,
    AssinantePublicResponse,
    AssinanteRequest,
    AssinantesListResponse,
    MensagemResponse,
)
from services.alerta_service import (
    AlertaServiceError,
    AlertaServiceErrorCode,
    DesativarAssinante,
    ListarAssinantes,
    RegistrarAssinante,
)

router = APIRouter(tags=["alertas"])


class AlertaAPIError(Exception):
    def __init__(self, status_code: int, error: AlertaErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    status_code: int
    error: AlertaErrorCode
    message: str


_ERROR_DETAILS = {
    AlertaServiceErrorCode.ASSINANTE_NAO_ENCONTRADO: _HTTPErrorDetails(
        404,
        "assinante_nao_encontrado",
        "Assinante não encontrado.",
    ),
}


@router.post("/alertas/assinantes", response_model=AssinanteCreatedResponse, status_code=201)
def registrar_assinante(
    payload: AssinanteRequest,
    registrador: RegistrarAssinante = Depends(get_alerta_registrador),
) -> AssinanteCreatedResponse:
    criado = registrador.registrar(projeto_id=payload.projeto_id, url=payload.url)
    return AssinanteCreatedResponse(
        id=criado.id,
        projeto_id=criado.projeto_id,
        url=criado.url,
        secret=criado.secret,
    )


@router.patch("/alertas/assinantes/{assinante_id}/desativar", response_model=MensagemResponse, status_code=200)
def desativar_assinante(
    assinante_id: str,
    desativador: DesativarAssinante = Depends(get_alerta_desativador),
) -> MensagemResponse:
    try:
        desativador.desativar(assinante_id=assinante_id)
    except AlertaServiceError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise AlertaAPIError(details.status_code, details.error, details.message) from exc
    return MensagemResponse(message="Assinante desativado com sucesso.")


@router.get("/alertas/assinantes", response_model=AssinantesListResponse, status_code=200)
def listar_assinantes(
    listador: ListarAssinantes = Depends(get_alerta_listador),
) -> AssinantesListResponse:
    assinantes = listador.listar()
    return AssinantesListResponse(
        assinantes=[
            AssinantePublicResponse(
                id=a.id,
                projeto_id=a.projeto_id,
                url=a.url,
                ativa=a.ativa,
                criado_em=a.criado_em,
            )
            for a in assinantes
        ]
    )
