#!/usr/bin/env python3
"""Gera um inventário anonimizado e somente leitura de vecs.documentos_metro."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_SQL = RAIZ / "src" / "database" / "inventario_rag.sql"
COLECAO = "vecs.documentos_metro"
TIMEOUT_CONEXAO_S = 8
TIMEOUT_CONSULTA_MS = 15_000


class InventarioError(RuntimeError):
    """Falha esperada de configuração ou pré-condição do inventário."""


def _argumentos() -> argparse.Namespace:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument(
        "--saida",
        type=Path,
        help="Também salva o JSON anonimizado neste caminho.",
    )
    return analisador.parse_args()


def _dsn() -> str:
    load_dotenv(RAIZ / ".env")
    valor = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not valor:
        raise InventarioError(
            "SUPABASE_DB_URL não configurada. Defina a connection string PostgreSQL "
            "do Supabase no .env."
        )
    return valor


def _sql() -> str:
    try:
        return ARQUIVO_SQL.read_text(encoding="utf-8")
    except OSError as erro:
        raise InventarioError(f"Não foi possível ler {ARQUIVO_SQL}: {erro}") from erro


def _executar(dsn: str, consulta: str) -> dict:
    conexao = None
    transacao_aberta = False
    try:
        conexao = psycopg.connect(
            dsn,
            autocommit=True,
            connect_timeout=TIMEOUT_CONEXAO_S,
        )
        conexao.execute("BEGIN TRANSACTION READ ONLY")
        transacao_aberta = True
        conexao.execute(f"SET LOCAL statement_timeout = {TIMEOUT_CONSULTA_MS}")

        existe = conexao.execute(
            "SELECT to_regclass(%s) IS NOT NULL",
            (COLECAO,),
        ).fetchone()[0]
        if not existe:
            raise InventarioError(
                f"A coleção {COLECAO} não existe no banco configurado."
            )

        # Perguntado ao servidor, e nao afirmado por nos. Este relatorio existe
        # para ser evidencia anexada a um MR, e um campo que so pode sair `true`
        # nao prova nada a quem revisa: prova que a linha foi escrita. Aqui,
        # `false` e um valor alcancavel, e e isso que da sentido a conferencia.
        somente_leitura = conexao.execute(
            "SELECT current_setting('transaction_read_only')"
        ).fetchone()[0] == "on"

        secoes: defaultdict[str, list[dict]] = defaultdict(list)
        for nome, item in conexao.execute(consulta).fetchall():
            secoes[nome].append(item)

        return {
            "colecao": COLECAO,
            "colecao_existe": True,
            "gerado_em_utc": datetime.now(UTC).isoformat(),
            "transacao_somente_leitura": somente_leitura,
            "resultados": dict(secoes),
        }
    except psycopg.Error as erro:
        raise InventarioError(
            f"Falha ao consultar o PostgreSQL: {type(erro).__name__}: {erro}"
        ) from erro
    finally:
        if conexao is not None:
            if transacao_aberta:
                with suppress(psycopg.Error):
                    conexao.execute("ROLLBACK")
            conexao.close()


def _serializar(relatorio: dict) -> str:
    return json.dumps(relatorio, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _caminho_de_saida(caminho: Path) -> Path:
    resolvido = caminho.expanduser().resolve()
    if resolvido == RAIZ or RAIZ in resolvido.parents:
        raise InventarioError(
            "A evidência não pode ser salva dentro do repositório. "
            "Use um caminho externo, como /tmp/inventario-rag.json."
        )
    return resolvido


def _salvar(caminho: Path, conteudo: str) -> None:
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    except OSError as erro:
        raise InventarioError(f"Não foi possível salvar {caminho}: {erro}") from erro


def main() -> int:
    argumentos = _argumentos()
    try:
        saida = (
            _caminho_de_saida(argumentos.saida)
            if argumentos.saida is not None
            else None
        )
        relatorio = _executar(_dsn(), _sql())
        conteudo = _serializar(relatorio)
        sys.stdout.write(conteudo)
        if saida is not None:
            _salvar(saida, conteudo)
        return 0
    except InventarioError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
