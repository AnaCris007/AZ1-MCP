# =============================================================================
# caminhos.py — Onde ficam os dados e onde vão parar os resultados
# =============================================================================
# Existe por um motivo concreto: até este arquivo, cada módulo resolvia os
# próprios caminhos com `Path(__file__).resolve().parent / "dados" / ...`,
# repetido em três arquivos. O efeito prático foi que o nome do dataset estava
# escrito ERRADO nos três ao mesmo tempo — `intencoes_exemplo.csv` em vez de
# `intencoes_exemplos.csv` — e o `--prever` quebrava com FileNotFoundError.
# Caminho repetido é caminho que diverge; aqui ele é declarado uma vez.
#
# A DISTINÇÃO QUE ORGANIZA ESTE ARQUIVO: ENTRADA x SAÍDA
# ------------------------------------------------------
# Os dois tipos de arquivo têm ciclos de vida opostos e por isso NÃO moram
# juntos.
#
# DADOS DE ENTRADA são parte do pacote. Versionados, pequenos, alterados por
# pessoas, e sem eles o código não roda. Ficam em `pln/dados/` e viajam dentro
# do wheel — é o que faz o experimento funcionar depois de um `pip install`,
# fora da pasta do repositório.
#
# RESULTADOS são saída de execução. Gerados por máquina, sobrescritos a cada
# rodada, e o código roda perfeitamente sem eles. Ficam em `resultados/`, na
# RAIZ do repositório, fora de `src/`. Manter saída gerada dentro do
# código-fonte é o que fazia um `.joblib` binário aparecer no diff de um
# módulo Python.
#
# POR QUE A RAIZ É PROCURADA, E NÃO FIXADA
# ----------------------------------------
# `resultados/` não pode ser resolvido a partir de `__file__`: uma vez
# instalado, o pacote está em site-packages, onde não existe raiz de
# repositório nenhuma. A busca abaixo sobe a árvore até achar o `pyproject.toml`
# e, se não achar, usa o diretório de trabalho. O comportamento fica previsível
# nos dois cenários: dentro do repositório grava sempre em `<repo>/resultados`,
# de qualquer subpasta; fora dele, grava em `./resultados`.
# =============================================================================

from __future__ import annotations

from pathlib import Path

# -----------------------------------------------------------------------------
# Entrada — dados versionados, empacotados junto com o código
# -----------------------------------------------------------------------------

DIR_PACOTE = Path(__file__).resolve().parent


# Normalmente é `pln/dados/`, ao lado deste arquivo — dentro do pacote, seja no
# repositório ou instalado em site-packages.
#
# O fallback existe para o arquivo único de `entregas/`, que é uma cópia gerada
# deste código morando FORA do pacote: lá, `DIR_PACOTE / "dados"` não existe, e
# a única referência possível é o repositório. Sem isso, a entrega rodaria só
# depois de alguém copiar o CSV para o lado dela.
def dir_dados() -> Path:
    ao_lado = DIR_PACOTE / "dados"
    if ao_lado.is_dir():
        return ao_lado

    raiz = encontrar_raiz_do_projeto()
    if raiz is not None and (raiz / "src" / "pln" / "dados").is_dir():
        return raiz / "src" / "pln" / "dados"

    # Nenhum dos dois: devolve o caminho canônico assim mesmo, para que o erro
    # seja um FileNotFoundError apontando o lugar certo em vez de um None.
    return ao_lado


# -----------------------------------------------------------------------------
# Saída — artefatos gerados, fora de src/
# -----------------------------------------------------------------------------


# `pyproject.toml` é o marcador de raiz porque é o arquivo que define o
# projeto: se ele está lá, aquela é a raiz. `.git` serviria, mas some quando
# alguém baixa o código como .zip.
def encontrar_raiz_do_projeto(a_partir_de: Path | None = None) -> Path | None:
    inicio = (a_partir_de or DIR_PACOTE).resolve()
    for diretorio in (inicio, *inicio.parents):
        if (diretorio / "pyproject.toml").is_file():
            return diretorio
    return None


def dir_resultados() -> Path:
    raiz = encontrar_raiz_do_projeto() or Path.cwd()
    return raiz / "resultados"


# -----------------------------------------------------------------------------
# Os caminhos concretos, derivados depois de as funções existirem
# -----------------------------------------------------------------------------

DIR_DADOS = dir_dados()

# O dataset de exemplo. Trocá-lo é um argumento de linha de comando
# (`--dataset`), não uma edição aqui.
DATASET_PADRAO = DIR_DADOS / "intencoes_exemplos.csv"

DIR_RESULTADOS = dir_resultados()

# O modelo treinado que `classificador.py` grava e `--prever` lê.
MODELO_PADRAO = DIR_RESULTADOS / "classificador.joblib"


# Chamado por quem vai ESCREVER. Deixar o mkdir aqui evita que cada módulo
# repita `caminho.parent.mkdir(parents=True, exist_ok=True)` — a mesma
# duplicação que originou o bug documentado no topo deste arquivo.
def garantir_dir_de_resultados() -> Path:
    destino = dir_resultados()
    destino.mkdir(parents=True, exist_ok=True)
    return destino
