from __future__ import annotations

from dataclasses import dataclass

from rag import indexador
from rag.embedder import vetorizar_um


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

    # vecs aceita no máximo uma entrada por filtro: dois critérios exigem $and.
    condicoes: list[dict] = []
    if projeto_id:
        condicoes.append({"projeto_id": {"$eq": projeto_id}})
    if tipo_documento:
        condicoes.append({"tipo_documento": {"$eq": tipo_documento}})

    filtro: dict | None = None
    if len(condicoes) == 1:
        filtro = condicoes[0]
    elif condicoes:
        filtro = {"$and": condicoes}

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
