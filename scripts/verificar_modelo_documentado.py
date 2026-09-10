"""Verifica se documento, script de criação e banco descrevem o mesmo modelo.

O risco que este script existe para eliminar é o de a Seção 3.6.6 do
`docs/Projeto.md` envelhecer em silêncio: uma definição transcrita em documento
não falha quando o banco muda, ela apenas passa a mentir. Aqui a divergência
vira saída não-zero.

Compara três fontes, tabela a tabela e coluna a coluna:

  1. o bloco SQL da Seção 3.6.6 de docs/Projeto.md;
  2. src/database/01_create_database.sql, que é a fonte de verdade;
  3. o banco em execução, lido do information_schema (opcional).

O banco só é consultado quando SUPABASE_DB_URL está definida. A leitura usa o
psycopg2 quando ele existe e, caso contrário, o cliente `psql` — que quem roda
os scripts de src/database já tem instalado. Sem nenhum dos dois, as duas
primeiras fontes ainda são comparadas entre si, de modo que a verificação
continue útil em qualquer máquina, inclusive na CI.

Uso:
    python scripts/verificar_modelo_documentado.py
    python scripts/verificar_modelo_documentado.py --sem-banco
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / "docs" / "Projeto.md"
DDL = RAIZ / "src" / "database" / "01_create_database.sql"

SCHEMAS = ("portfolio", "auditoria")

# Linhas que abrem uma restrição de tabela, e não uma coluna.
INICIO_DE_RESTRICAO = re.compile(
    r"^(PRIMARY|UNIQUE|CHECK|CONSTRAINT|FOREIGN|EXCLUDE)\b", re.IGNORECASE
)
CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<schema>\w+)\.(?P<tabela>\w+)\s*\((?P<corpo>.*?)\n\s*\);",
    re.IGNORECASE | re.DOTALL,
)


def _tirar_comentarios(sql: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", linha) for linha in sql.split("\n"))


def _dividir_no_nivel_zero(corpo: str) -> list[str]:
    """Quebra o corpo do CREATE TABLE nas vírgulas fora de parênteses.

    Uma quebra ingênua por vírgula partiria `NUMERIC(5,2)` e as listas dos
    CHECK ao meio, produzindo colunas fantasmas.
    """
    partes, atual, profundidade, aspas = [], [], 0, False
    for ch in corpo:
        if ch == "'":
            aspas = not aspas
        if not aspas:
            if ch == "(":
                profundidade += 1
            elif ch == ")":
                profundidade -= 1
            elif ch == "," and profundidade == 0:
                partes.append("".join(atual))
                atual = []
                continue
        atual.append(ch)
    if atual:
        partes.append("".join(atual))
    return partes


def extrair(sql: str) -> dict[str, list[str]]:
    """Devolve {"schema.tabela": [colunas...]} a partir de um texto SQL."""
    sql = _tirar_comentarios(sql)
    modelo: dict[str, list[str]] = {}
    for m in CREATE_TABLE.finditer(sql):
        if m.group("schema").lower() not in SCHEMAS:
            continue
        colunas = []
        for parte in _dividir_no_nivel_zero(m.group("corpo")):
            parte = parte.strip()
            if not parte or INICIO_DE_RESTRICAO.match(parte):
                continue
            colunas.append(parte.split()[0].strip('"').lower())
        modelo[f"{m.group('schema').lower()}.{m.group('tabela').lower()}"] = colunas
    return modelo


def do_documento() -> dict[str, list[str]]:
    texto = DOC.read_text(encoding="utf-8")
    inicio = texto.index("### 3.6.6 Definição física em SQL")
    fim = texto.index("### 3.6.7", inicio)
    blocos = re.findall(r"```sql\n(.*?)```", texto[inicio:fim], re.DOTALL)
    if not blocos:
        raise SystemExit("Nenhum bloco ```sql encontrado na Seção 3.6.6.")
    return extrair("\n".join(blocos))


CONSULTA_COLUNAS = """
    SELECT c.table_schema || '.' || c.table_name, c.column_name
      FROM information_schema.columns c
      JOIN information_schema.tables t
        ON t.table_schema = c.table_schema
       AND t.table_name = c.table_name
     WHERE c.table_schema IN ('portfolio', 'auditoria')
       AND t.table_type = 'BASE TABLE'
     ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""


def _por_psycopg2(url: str) -> dict[str, list[str]] | None:
    try:
        import psycopg2
    except ImportError:
        return None
    modelo: dict[str, list[str]] = {}
    with psycopg2.connect(url) as conexao, conexao.cursor() as cur:
        cur.execute(CONSULTA_COLUNAS)
        for tabela, coluna in cur.fetchall():
            modelo.setdefault(tabela, []).append(coluna)
    return modelo


def _por_psql(url: str) -> dict[str, list[str]] | None:
    """Lê o schema pelo cliente de linha de comando, sem driver Python."""
    import shutil
    import subprocess

    if not shutil.which("psql"):
        return None
    saida = subprocess.run(
        ["psql", url, "-X", "-A", "-t", "-F", "\t", "-c", CONSULTA_COLUNAS],
        capture_output=True, text=True,
    )
    if saida.returncode != 0:
        print(f"  (psql falhou: {saida.stderr.strip().splitlines()[-1:]})")
        return None
    modelo: dict[str, list[str]] = {}
    for linha in saida.stdout.splitlines():
        if "\t" not in linha:
            continue
        tabela, coluna = linha.split("\t", 1)
        modelo.setdefault(tabela.strip(), []).append(coluna.strip())
    return modelo


def do_banco() -> dict[str, list[str]] | None:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        print("  (SUPABASE_DB_URL não definida — banco não verificado)")
        return None
    modelo = _por_psycopg2(url) or _por_psql(url)
    if modelo is None:
        print("  (sem psycopg2 e sem psql — banco não verificado)")
    return modelo


def comparar(nome_a: str, a: dict[str, list[str]],
             nome_b: str, b: dict[str, list[str]]) -> list[str]:
    """Divergências entre dois modelos. Ignora a ordem das colunas."""
    problemas = []
    for tabela in sorted(set(a) - set(b)):
        problemas.append(f"tabela {tabela}: em {nome_a}, ausente em {nome_b}")
    for tabela in sorted(set(b) - set(a)):
        problemas.append(f"tabela {tabela}: em {nome_b}, ausente em {nome_a}")
    for tabela in sorted(set(a) & set(b)):
        ca, cb = set(a[tabela]), set(b[tabela])
        for col in sorted(ca - cb):
            problemas.append(f"{tabela}.{col}: em {nome_a}, ausente em {nome_b}")
        for col in sorted(cb - ca):
            problemas.append(f"{tabela}.{col}: em {nome_b}, ausente em {nome_a}")
    return problemas


def main() -> int:
    sem_banco = "--sem-banco" in sys.argv

    doc = do_documento()
    ddl = extrair(DDL.read_text(encoding="utf-8"))
    print(f"Seção 3.6.6 do Projeto.md : {len(doc):2d} tabelas, "
          f"{sum(len(v) for v in doc.values()):3d} colunas")
    print(f"01_create_database.sql    : {len(ddl):2d} tabelas, "
          f"{sum(len(v) for v in ddl.values()):3d} colunas")

    banco = None if sem_banco else do_banco()
    if banco is not None:
        print(f"Banco em execução         : {len(banco):2d} tabelas, "
              f"{sum(len(v) for v in banco.values()):3d} colunas")

    problemas = comparar("documento", doc, "script", ddl)
    if banco is not None:
        problemas += comparar("script", ddl, "banco", banco)

    print()
    if problemas:
        print(f"DIVERGÊNCIAS ({len(problemas)}):")
        for p in problemas:
            print(f"  - {p}")
        print("\nAtualize a Seção 3.6.6, o script ou o banco até que coincidam.")
        return 1

    if banco is None:
        print("OK — documento e script descrevem o mesmo modelo.")
        print("ATENÇÃO: o banco não foi verificado; a coerência com ele "
              "permanece desconhecida.")
        return 0

    print("OK — documento, script e banco descrevem o mesmo modelo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
