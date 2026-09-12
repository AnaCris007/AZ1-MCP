from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

AlertaErrorCode = Literal[
    "url_invalida",
    "assinante_nao_encontrado",
    "internal_error",
]


class AssinanteRequest(BaseModel):
    projeto_id: str
    url: str

    @field_validator("url")
    @classmethod
    def validar_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("URL deve começar com https://")
        return v


class AssinanteCreatedResponse(BaseModel):
    id: str
    projeto_id: str
    url: str
    secret: str  # retornado apenas na criação


class AssinantePublicResponse(BaseModel):
    id: str
    projeto_id: str
    url: str
    ativa: bool
    criado_em: str


class AssinantesListResponse(BaseModel):
    assinantes: list[AssinantePublicResponse]


class MensagemResponse(BaseModel):
    message: str
