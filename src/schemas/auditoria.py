from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AuditoriaErrorCode = Literal["internal_error"]


class ConsultaLog(BaseModel):
    id: str
    conversa_id: str
    papel: str
    conteudo: str
    tempo_processamento_ms: int | None
    criada_em: str


class AuditoriaListResponse(BaseModel):
    consultas: list[ConsultaLog]
