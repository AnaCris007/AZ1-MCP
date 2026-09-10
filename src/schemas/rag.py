from __future__ import annotations

from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    query: str
    n_resultados: int = Field(default=5, ge=1, le=20)
    projeto_id: str | None = None
    tipo_documento: str | None = None


class RagResultado(BaseModel):
    texto: str
    score: float
    projeto_id: str
    tipo_documento: str
    secao: str
    arquivo_origem: str


class RagSearchResponse(BaseModel):
    query: str
    resultados: list[RagResultado]
