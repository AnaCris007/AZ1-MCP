# Caminhos de entrada e saída do pacote, declarados num lugar só.

from __future__ import annotations

from pathlib import Path

DIR_PACOTE = Path(__file__).resolve().parent


def dir_dados() -> Path:
    return DIR_PACOTE / "dados"


# `resultados/` não pode ser resolvido a partir de `__file__`: instalado, o
# pacote está em site-packages, fora de qualquer repositório. `pyproject.toml`
# marca a raiz; `.git` não serve porque some no download como .zip.
def encontrar_raiz_do_projeto(a_partir_de: Path | None = None) -> Path | None:
    inicio = (a_partir_de or DIR_PACOTE).resolve()
    for diretorio in (inicio, *inicio.parents):
        if (diretorio / "pyproject.toml").is_file():
            return diretorio
    return None


def dir_resultados() -> Path:
    raiz = encontrar_raiz_do_projeto() or Path.cwd()
    return raiz / "resultados"


DIR_DADOS = dir_dados()

# Três arquivos, e uma relação entre eles: o POOL é autoral e contém todos os
# exemplos; os outros dois são GERADOS por `python -m pln.particao` e não devem
# ser editados à mão.
#
# São arquivos separados, e não uma coluna `particao` num CSV só, de propósito:
# assim `experimento.py`, `ajuste_fino.py` e `bancada.py` ficam INCAPAZES de
# enxergar o teste, em vez de apenas instruídos a não enxergá-lo. Nenhum deles
# precisou mudar uma linha.
DATASET_POOL = DIR_DADOS / "intencoes_pool.csv"
DATASET_PADRAO = DIR_DADOS / "intencoes_exemplos.csv"
DATASET_TESTE = DIR_DADOS / "intencoes_teste.csv"

DIR_RESULTADOS = dir_resultados()
MODELO_PADRAO = DIR_RESULTADOS / "classificador.joblib"


def garantir_dir_de_resultados() -> Path:
    destino = dir_resultados()
    destino.mkdir(parents=True, exist_ok=True)
    return destino
