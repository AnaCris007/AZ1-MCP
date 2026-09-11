#!/usr/bin/env python3
"""
Pipeline de ingestão e indexação RAG para a base sintética do PMO.

Fluxo: DOCX/XLSX → parsers → chunker → embedder (Gemini) → Supabase/pgvector

Uso:
    python scripts/indexar_documentos.py <pasta_base>

Exemplo:
    python scripts/indexar_documentos.py ~/Downloads/base_sintetica_metro

Variáveis de ambiente necessárias:
    GEMINI_API_KEY     — chave da API Gemini (obrigatória)
    SUPABASE_DB_URL    — connection string PostgreSQL do Supabase (obrigatória)

Pré-requisito no Supabase:
    Habilite pgvector via SQL Editor:
        create extension if not exists vector;

ATENÇÃO — MIGRAÇÃO DE COLEÇÃO EXISTENTE:
    A dimensão do embedding passou de 3072 para 1536 e o `task_type` passou a
    distinguir documento de consulta. Uma coleção indexada antes disso guarda
    vetores incompatíveis: o tamanho não bate e a projeção é outra. Reindexar
    por cima não corrige, porque o upsert só substitui os chunks que reaparecem
    com o mesmo id.

    Antes da primeira execução com esta versão, derrube a coleção:
        drop table if exists vecs."documentos_metro";
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que src/ está no sys.path quando o script é rodado diretamente
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from rag import indexador  # noqa: E402
from rag.chunker import chunkar  # noqa: E402
from rag.embedder import vetorizar_documentos  # noqa: E402
from rag.parsers import extrair  # noqa: E402


def indexar_pasta(pasta_base: Path) -> None:
    arquivos = sorted(
        list(pasta_base.rglob("*.docx")) + list(pasta_base.rglob("*.xlsx"))
    )

    if not arquivos:
        print("Nenhum arquivo .docx ou .xlsx encontrado.")
        return

    print(f"Encontrados {len(arquivos)} arquivos. Iniciando indexação...\n")
    total_chunks = 0
    total_arquivos = 0

    for caminho in arquivos:
        label = caminho.relative_to(pasta_base)
        print(f"  [{label}]", end=" ", flush=True)

        textos = extrair(caminho)
        if not textos:
            print("→ sem conteúdo, pulado.")
            continue

        chunks = chunkar(textos)
        embeddings = vetorizar_documentos([c.texto for c in chunks])
        n = indexador.indexar(chunks, embeddings)

        print(f"→ {len(textos)} unidades → {n} chunks indexados")
        total_chunks += n
        total_arquivos += 1

    print("\nIndexação concluída.")
    print(f"  Arquivos processados : {total_arquivos}/{len(arquivos)}")
    print(f"  Chunks no índice     : {indexador.contar()}")

    # O índice é criado aqui, e não a cada arquivo, porque o HNSW é construído
    # sobre o conjunto inteiro: refazê-lo a cada lote custaria caro e daria no
    # mesmo. Até esta versão `criar_indice` não tinha chamador nenhum, ou seja,
    # a coleção existia sem índice e toda busca varria a tabela inteira.
    print()
    print("Criando índice HNSW...", end=" ", flush=True)
    try:
        indexador.criar_indice()
        print("pronto.")
    except Exception as erro:  # noqa: BLE001 — a busca funciona sem índice, só que devagar
        # Os chunks já foram gravados, então não se perde trabalho. Sem índice a
        # busca continua respondendo por varredura sequencial, com latência
        # crescendo linear com o tamanho da base: vale avisar alto e seguir.
        print("FALHOU.")
        print(f"  {type(erro).__name__}: {erro}")
        print("  Os chunks estão indexados, mas a busca fará varredura sequencial.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    pasta = Path(sys.argv[1]).expanduser().resolve()
    if not pasta.is_dir():
        print(f"Erro: '{pasta}' não é um diretório válido.")
        sys.exit(1)

    indexar_pasta(pasta)
