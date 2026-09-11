from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import vecs
from sqlalchemy import text
from vecs import IndexMeasure, IndexMethod

from rag.chunker import Chunk
from rag.embedder import DIMENSAO_EMBEDDING

NOME_COLECAO = "documentos_metro"

# `DIMENSAO_EMBEDDING` vem de `embedder` em vez de ser declarada aqui: são duas
# pontas da mesma decisão, e duas constantes separadas divergem em silêncio —
# a coleção aceitaria vetores de tamanho diferente do que o modelo produz e o
# erro só apareceria no upsert.


def _db_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL não configurada. Use a connection string PostgreSQL "
            "(Supabase → Settings → Database → Connection string → URI)."
        )
    return url


@lru_cache(maxsize=1)
def _cliente() -> vecs.Client:
    return vecs.create_client(_db_url())


def obter_colecao() -> vecs.Collection:
    return _cliente().get_or_create_collection(
        name=NOME_COLECAO,
        dimension=DIMENSAO_EMBEDDING,
    )


def _chunk_id(chunk: Chunk) -> str:
    conteudo = f"{chunk.arquivo_origem}::{chunk.chunk_index}::{chunk.texto[:60]}"
    return hashlib.md5(conteudo.encode()).hexdigest()


def indexar(chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    """Armazena chunks com seus embeddings. Upsert — seguro para re-indexar."""
    if not chunks:
        return 0

    colecao = obter_colecao()
    records = [
        (
            _chunk_id(c),
            embedding,
            {
                "projeto_id": c.projeto_id,
                "tipo_documento": c.tipo_documento,
                "arquivo_origem": c.arquivo_origem,
                "secao": c.secao,
                "texto": c.texto,
            },
        )
        for c, embedding in zip(chunks, embeddings)
    ]
    colecao.upsert(records=records)
    return len(records)


def criar_indice() -> None:
    """Cria índice HNSW cosine. Chamar uma vez após a carga inicial completa.

    Só funciona porque `DIMENSAO_EMBEDDING` cabe no limite de 2000 dimensões
    que o pgvector impõe a índices HNSW e IVFFlat. Sem índice, `buscar` cai em
    varredura sequencial da coleção inteira.
    """
    obter_colecao().create_index(
        method=IndexMethod.hnsw,
        measure=IndexMeasure.cosine_distance,
        replace=True,
    )


def buscar(
    embedding_consulta: list[float],
    *,
    n_resultados: int = 5,
    filtro: dict | None = None,
) -> list[dict]:
    """Busca semântica: retorna os n_resultados chunks mais próximos do embedding."""
    colecao = obter_colecao()
    resultados = colecao.query(
        data=embedding_consulta,
        limit=n_resultados,
        filters=filtro or {},
        include_metadata=True,
        include_value=True,
    )
    # vecs retorna (id, distancia, metadata) quando include_value=True + include_metadata=True
    return [
        {
            "id": r[0],
            "distancia": r[1],
            "metadados": {k: v for k, v in r[2].items() if k != "texto"},
            "texto": r[2].get("texto", ""),
        }
        for r in resultados
    ]


def contar() -> int:
    """Retorna o número total de chunks indexados."""
    with _cliente().Session() as session:
        n = session.execute(
            text(f'SELECT COUNT(*) FROM vecs."{NOME_COLECAO}"')
        ).scalar()
    return int(n or 0)
