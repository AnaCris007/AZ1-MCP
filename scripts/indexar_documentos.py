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
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que src/ está no sys.path quando o script é rodado diretamente
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv

load_dotenv()

from rag.parsers import extrair
from rag.chunker import chunkar
from rag.embedder import vetorizar
from rag import indexador


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
        embeddings = vetorizar([c.texto for c in chunks])
        n = indexador.indexar(chunks, embeddings)

        print(f"→ {len(textos)} unidades → {n} chunks indexados")
        total_chunks += n
        total_arquivos += 1

    print(f"\nIndexação concluída.")
    print(f"  Arquivos processados : {total_arquivos}/{len(arquivos)}")
    print(f"  Chunks no índice     : {indexador.contar()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    pasta = Path(sys.argv[1]).expanduser().resolve()
    if not pasta.is_dir():
        print(f"Erro: '{pasta}' não é um diretório válido.")
        sys.exit(1)

    indexar_pasta(pasta)
