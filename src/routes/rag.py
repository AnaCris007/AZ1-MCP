from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from az1_api.dependencies import get_document_searcher
from schemas.rag import RagResultado, RagSearchRequest, RagSearchResponse

router = APIRouter(tags=["rag"])

# A busca chega por injeção em vez de import direto no módulo: é o que permite
# substituí-la em teste sem tocar no Supabase nem na API do Gemini.
Buscador = Annotated[Callable, Depends(get_document_searcher)]


@router.post("/rag/search", response_model=RagSearchResponse)
def search_rag(payload: RagSearchRequest, buscar: Buscador) -> RagSearchResponse:
    resultados = buscar(
        payload.query,
        n_resultados=payload.n_resultados,
        projeto_id=payload.projeto_id,
        tipo_documento=payload.tipo_documento,
    )
    return RagSearchResponse(
        query=payload.query,
        resultados=[
            RagResultado(
                texto=r.texto,
                score=r.score,
                projeto_id=r.projeto_id,
                tipo_documento=r.tipo_documento,
                secao=r.secao,
                arquivo_origem=r.arquivo_origem,
                chunk_id=r.chunk_id,
            )
            for r in resultados
        ],
    )
