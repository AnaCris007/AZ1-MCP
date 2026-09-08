from __future__ import annotations

from dataclasses import dataclass

from rag.embedder import vetorizar_um
from rag import indexador


@dataclass(frozen=True)
class ResultadoBusca:
    texto: str
    score: float
    projeto_id: str
    tipo_documento: str
    secao: str
    arquivo_origem: str


def buscar(
    query: str,
    *,
    n_resultados: int = 5,
    projeto_id: str | None = None,
    tipo_documento: str | None = None,
) -> list[ResultadoBusca]:
    """Vetoriza a query e busca os chunks mais relevantes no índice."""
    embedding = vetorizar_um(query)

    filtro: dict | None = None
    if projeto_id or tipo_documento:
        filtro = {}
        if projeto_id:
            filtro["projeto_id"] = {"$eq": projeto_id}
        if tipo_documento:
            filtro["tipo_documento"] = {"$eq": tipo_documento}

    brutos = indexador.buscar(embedding, n_resultados=n_resultados, filtro=filtro)

    return [
        ResultadoBusca(
            texto=r["texto"],
            score=float(1 - r["distancia"]),  # cosine distance → similarity score
            projeto_id=r["metadados"].get("projeto_id", ""),
            tipo_documento=r["metadados"].get("tipo_documento", ""),
            secao=r["metadados"].get("secao", ""),
            arquivo_origem=r["metadados"].get("arquivo_origem", ""),
        )
        for r in brutos
    ]
