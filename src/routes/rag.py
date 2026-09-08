from __future__ import annotations

from fastapi import APIRouter

from rag.retriever import buscar
from schemas.rag import RagResultado, RagSearchRequest, RagSearchResponse

router = APIRouter(tags=["rag"])


@router.post("/rag/search", response_model=RagSearchResponse)
def search_rag(payload: RagSearchRequest) -> RagSearchResponse:
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
            )
            for r in resultados
        ],
    )
