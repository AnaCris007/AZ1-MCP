# Busca dos hiperparâmetros do modelo do produto: suavização x priori, sobre os
# melhores pré-processamentos e vetorizações do experimento.
#
# Complementa `experimento.py`, que varia o texto e fixa o modelo. Aqui é o
# inverso, e por isso o experimento roda primeiro: o texto vem do relatório que
# ele grava. Sem o relatório, cai numa lista mínima embutida e avisa.
#
# É uma busca em estágios e não encontra o ótimo global; o corte é ajustável em
# `--top-pre` (0 = todos os pré-processamentos do relatório).
#
#     python -m pln.experimento
#     python -m pln.ajuste_fino
#     python -m pln.ajuste_fino --top-pre 20 --k 10

from __future__ import annotations

import argparse
import csv
import itertools
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_val_score

from pln.caminhos import DATASET_PADRAO, dir_resultados, garantir_dir_de_resultados
from pln.classificador import carregar_dataset, construir_classificador
from pln.preprocessamento import (
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
)
from pln.vetorizacao import ConfigVetorizacao, todas_as_vetorizacoes

SEMENTE = 42
LARGURA = 118

# Suavização de Laplace/Lidstone. O padrão do scikit-learn é 1,0.
GRADE_ALPHA: tuple[float, ...] = (0.01, 0.05, 0.1, 0.5, 1.0, 2.0)

# `False` fixa as prioris em uniformes.
GRADE_FIT_PRIOR: tuple[bool, ...] = (True, False)

# O mínimo indispensável quando não há relatório do experimento para ler.
PRE_PROCESSAMENTOS_DE_EMERGENCIA: tuple[ConfigPreprocessamento, ...] = (
    ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT),
    ConfigPreprocessamento(minusculas=True, tokenizacao=Tokenizacao.REGEX),
    ConfigPreprocessamento(
        minusculas=True, remover_pontuacao=True,
        stopwords=ModoStopwords.PRESERVAR_NEGACOES, tokenizacao=Tokenizacao.REGEX,
    ),
)


@dataclass(frozen=True)
class Candidato:
    config_pre: ConfigPreprocessamento
    config_vet: ConfigVetorizacao
    suavizacao: float
    fit_prior: bool

    def descrever(self) -> str:
        return (
            f"s={self.suavizacao:<7g} prior={'treino' if self.fit_prior else 'unif'} | "
            f"{self.config_vet.descrever()} | {self.config_pre.descrever()}"
        )


# O sufixo distingue de `experimento.Resultado`, que tem outros campos.
@dataclass
class ResultadoDoAjuste:
    candidato: Candidato
    f1_medio: float
    f1_desvio: float


# O CSV grava cada campo em coluna própria para permitir esta leitura sem
# interpretar a string de descrição, que é para humano.
def config_da_linha(linha: dict[str, str]) -> ConfigPreprocessamento:
    def booleano(nome: str) -> bool:
        return linha[nome].strip().lower() == "true"

    return ConfigPreprocessamento(
        minusculas=booleano("minusculas"),
        remover_acentos=booleano("remover_acentos"),
        remover_pontuacao=booleano("remover_pontuacao"),
        remover_numeros=booleano("remover_numeros"),
        stopwords=ModoStopwords(linha["stopwords"]),
        morfologia=ModoMorfologia(linha["morfologia"]),
        tokenizacao=Tokenizacao(linha["tokenizacao"]),
    )


# Distintos, porque o CSV tem uma linha por (pré-processamento, vetorização) e o
# mesmo texto aparece repetido no topo do ranking.
def carregar_candidatos_de_texto(quantos: int) -> tuple[list[ConfigPreprocessamento], str]:
    caminho = dir_resultados() / "comparativo_preprocessamento.csv"
    if not caminho.is_file():
        return list(PRE_PROCESSAMENTOS_DE_EMERGENCIA), (
            f"⚠️  {caminho.name} não encontrado, usando a lista mínima embutida.\n"
            f"   Rode `python -m pln.experimento` primeiro para ajustar sobre os "
            f"pré-processamentos realmente medidos."
        )

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    distintos: list[ConfigPreprocessamento] = []
    ja_vistos: set[ConfigPreprocessamento] = set()
    for linha in linhas:
        config = config_da_linha(linha)
        if config not in ja_vistos:
            ja_vistos.add(config)
            distintos.append(config)
        if quantos and len(distintos) >= quantos:
            break

    quantidade = "todos os" if not quantos else f"os {len(distintos)} melhores"
    return distintos, f"Pré-processamentos: {quantidade} de {caminho.name} ({len(linhas)} linhas)."


# O classificador não é eixo de busca: é `MultinomialNB`, o mesmo que serviu de
# régua ao experimento. Trocá-lo aqui faria o pré-processamento ter sido
# escolhido para um modelo diferente do que roda em produção.
def montar_candidatos(configs_pre: list[ConfigPreprocessamento]) -> list[Candidato]:
    return [
        Candidato(config_pre, config_vet, suavizacao, fit_prior)
        for config_pre, config_vet in itertools.product(configs_pre, todas_as_vetorizacoes())
        for suavizacao, fit_prior in itertools.product(GRADE_ALPHA, GRADE_FIT_PRIOR)
    ]


# O pré-processamento é etapa do Pipeline e por isso é reaplicado dentro de cada
# dobra: mais lento, e o que impede vazamento do treino para o teste.
def medir(candidato: Candidato, textos: list[str], rotulos: list[str], k: int) -> ResultadoDoAjuste:
    modelo = construir_classificador(
        config_pre=candidato.config_pre,
        config_vet=candidato.config_vet,
        alpha=candidato.suavizacao,
        fit_prior=candidato.fit_prior,
    )
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    notas = cross_val_score(modelo, textos, rotulos, cv=dobras, scoring="f1_macro")
    desvio = statistics.stdev(notas) if len(notas) > 1 else 0.0
    return ResultadoDoAjuste(candidato, statistics.mean(notas), desvio)


def varrer(candidatos: list[Candidato], textos: list[str], rotulos: list[str], k: int) -> list[ResultadoDoAjuste]:
    resultados: list[ResultadoDoAjuste] = []
    for numero, candidato in enumerate(candidatos, start=1):
        resultados.append(medir(candidato, textos, rotulos, k))
        if sys.stdout.isatty() and numero % 10 == 0:
            print(f"\r  {numero}/{len(candidatos)} candidatos", end="", flush=True)

    if sys.stdout.isatty():
        print(f"\r  {len(candidatos)}/{len(candidatos)} candidatos")

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados


# As comparações pareadas abaixo dependem de o espaço de busca ser um produto
# cartesiano completo: se algum eixo passar a valer só para parte das
# combinações, nenhum grupo fica completo e as tabelas somem do relatório.


# O `str()` cru de um dataclass é ilegível na tabela.
def rotular(valor) -> str:
    if hasattr(valor, "descrever"):
        return valor.descrever()
    if hasattr(valor, "value"):
        return str(valor.value)
    return str(valor)


# Pareado: para cada combinação dos outros eixos, compara os valores deste entre
# si. Média solta atribuiria ao eixo uma diferença vinda do resto.
def comparar_eixo(resultados: list[ResultadoDoAjuste], eixo: str) -> list[tuple[str, float, int]]:
    outros = [c for c in ("config_pre", "config_vet", "suavizacao", "fit_prior") if c != eixo]

    grupos: dict[tuple, dict[str, float]] = {}
    for resultado in resultados:
        chave = tuple(getattr(resultado.candidato, campo) for campo in outros)
        grupos.setdefault(chave, {})[rotular(getattr(resultado.candidato, eixo))] = resultado.f1_medio

    rotulos = {r for g in grupos.values() for r in g}
    if len(rotulos) < 2:
        return []  # eixo constante: não há o que comparar

    completos = [g for g in grupos.values() if len(g) == len(rotulos)]
    if not completos:
        return []

    return sorted(
        ((rotulo, statistics.mean(g[rotulo] for g in completos), len(completos)) for rotulo in rotulos),
        key=lambda linha: linha[1],
        reverse=True,
    )


# Empate é "dentro de um desvio padrão da melhor". Simplicidade, em ordem: menos
# etapas, janela de n-grama menor, suavização mais próxima do padrão.
def escolher_mais_simples(resultados: list[ResultadoDoAjuste]) -> ResultadoDoAjuste:
    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatados = [r for r in resultados if r.f1_medio >= limiar]

    def custo(r: ResultadoDoAjuste) -> tuple:
        c = r.candidato
        return (
            len(c.config_pre.etapas_ativas_na_ordem()),
            c.config_vet.n_max,
            abs(c.suavizacao - 1.0),
            -r.f1_medio,
        )

    return min(empatados, key=custo)


# `descrever()` usa `|`, que delimita coluna em tabela markdown.
def escapar_para_tabela(texto: str) -> str:
    return texto.replace("|", "\\|")


# Precisa sair como Python válido e copiável: o `repr()` de um dataclass com
# enums imprime `<ModoStopwords.MANTER: 'manter'>`, que não compila.
def gerar_bloco_de_configuracao(candidato: Candidato) -> list[str]:
    padrao = ConfigPreprocessamento()
    argumentos = [
        f"{campo}={getattr(candidato.config_pre, campo)}"
        for campo in ("minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros")
        if getattr(candidato.config_pre, campo) != getattr(padrao, campo)
    ]
    if candidato.config_pre.stopwords is not padrao.stopwords:
        argumentos.append(f"stopwords=ModoStopwords.{candidato.config_pre.stopwords.name}")
    if candidato.config_pre.morfologia is not padrao.morfologia:
        argumentos.append(f"morfologia=ModoMorfologia.{candidato.config_pre.morfologia.name}")
    # Entra sempre, para registrar a escolha em vez de herdá-la do padrão.
    argumentos.append(f"tokenizacao=Tokenizacao.{candidato.config_pre.tokenizacao.name}")

    return [
        "```python",
        f"CONFIG_PRE_PADRAO = ConfigPreprocessamento({', '.join(argumentos)})",
        f"CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.{candidato.config_vet.modo.name}, "
        f"n_max={candidato.config_vet.n_max})",
        f"ALPHA_PADRAO      = {candidato.suavizacao!r}",
        f"FIT_PRIOR_PADRAO  = {candidato.fit_prior}",
        "```",
    ]

EIXOS_ANALISADOS = ("suavizacao", "fit_prior", "config_vet")

TITULOS_DOS_EIXOS = {
    "suavizacao": "SUAVIZAÇÃO",
    "fit_prior": "PROBABILIDADES A PRIORI",
    "config_vet": "VETORIZAÇÃO",
    "config_pre": "PRÉ-PROCESSAMENTO",
}


def imprimir_ranking_do_ajuste(resultados: list[ResultadoDoAjuste], top: int) -> None:
    print(f"\n{'#':>3}  {'F1-macro':>8}  {'±dp':>6}  configuração")
    print("-" * LARGURA)
    for posicao, r in enumerate(resultados[:top], start=1):
        print(f"{posicao:>3}  {r.f1_medio:>8.4f}  {r.f1_desvio:>6.4f}  {r.candidato.descrever()}")


def imprimir_eixos(resultados: list[ResultadoDoAjuste]) -> None:
    for eixo in EIXOS_ANALISADOS:
        linhas = comparar_eixo(resultados, eixo)
        if not linhas:
            continue
        cabecalho = f"{TITULOS_DOS_EIXOS[eixo]}, pareado em {linhas[0][2]} combinações"
        print(f"\n{cabecalho:^{LARGURA}}")
        print(f"{'opção':>24}  {'F1 médio':>10}  {'vs melhor':>12}")
        print("-" * LARGURA)
        topo = linhas[0][1]
        for rotulo, media, _ in linhas:
            print(f"{rotulo:>24}  {media:>10.4f}  {media - topo:>+12.4f}")


def escrever_relatorio_do_ajuste(
    resultados: list[ResultadoDoAjuste], escolhido: ResultadoDoAjuste, dataset: Path, k: int, origem: str
) -> Path:
    destino = garantir_dir_de_resultados() / "ajuste_fino.md"
    melhor = resultados[0]

    linhas = [
        "# Ajuste fino do classificador de intenções",
        "",
        f"- Dataset: `{dataset.name}`",
        f"- Validação cruzada estratificada de {k} dobras, semente {SEMENTE}",
        f"- Candidatos avaliados: {len(resultados)}",
        f"- {origem}",
        "",
        "Este relatório ajusta o MODELO. O que preparar do texto é decidido em",
        "`comparativo_preprocessamento.md`, por `experimento.py`.",
        "",
        "## Recomendação",
        "",
        f"- **Melhor absoluta:** {melhor.f1_medio:.4f} ± {melhor.f1_desvio:.4f} — "
        f"`{melhor.candidato.descrever()}`",
        f"- **Mais simples entre as empatadas:** {escolhido.f1_medio:.4f} — "
        f"`{escolhido.candidato.descrever()}`",
        "",
        "Valores para `classificador.py`:",
        "",
        *gerar_bloco_de_configuracao(escolhido.candidato),
    ]

    for eixo in EIXOS_ANALISADOS:
        comparacao = comparar_eixo(resultados, eixo)
        if not comparacao:
            continue
        linhas += [
            "", f"## {TITULOS_DOS_EIXOS[eixo].capitalize()}", "",
            f"Comparação **pareada** em {comparacao[0][2]} combinações idênticas nos demais eixos.",
            "", "| opção | F1 médio | vs melhor |", "|---|---|---|",
        ]
        topo = comparacao[0][1]
        for rotulo, media, _ in comparacao:
            linhas.append(f"| `{escapar_para_tabela(rotulo)}` | {media:.4f} | {media - topo:+.4f} |")

    linhas += ["", "## Ranking (top 30)", "", "| # | F1-macro | ±dp | configuração |", "|---|---|---|---|"]
    for posicao, r in enumerate(resultados[:30], start=1):
        linhas.append(
            f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | "
            f"`{escapar_para_tabela(r.candidato.descrever())}` |"
        )

    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ajusta os hiperparâmetros do classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--top", type=int, default=15, help="linhas mostradas no ranking")
    parser.add_argument("--top-pre", type=int, default=5,
                        help="quantos pré-processamentos do experimento entram na busca (0 = todos)")
    args = parser.parse_args(argv)

    textos, rotulos = carregar_dataset(args.dataset)
    configs_pre, origem = carregar_candidatos_de_texto(args.top_pre)
    candidatos = montar_candidatos(configs_pre)

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(origem)
    print(f"Vetorizações: {len(todas_as_vetorizacoes())}   Candidatos: {len(candidatos)}")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}\n")

    resultados = varrer(candidatos, textos, rotulos, args.k)

    print(f"\n{'=' * LARGURA}")
    print(f"{'AJUSTE FINO DO MODELO':^{LARGURA}}")
    print("=" * LARGURA)
    imprimir_ranking_do_ajuste(resultados, args.top)
    imprimir_eixos(resultados)

    escolhido = escolher_mais_simples(resultados)
    melhor = resultados[0]
    print(f"\n{'=' * LARGURA}")
    print(f"{'RECOMENDAÇÃO':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"Melhor absoluta : {melhor.f1_medio:.4f}  {melhor.candidato.descrever()}")
    empatados = sum(1 for r in resultados if r.f1_medio >= melhor.f1_medio - melhor.f1_desvio)
    print(f"Dentro de 1 desvio padrão da melhor: {empatados} de {len(resultados)} — empatadas na prática.")
    print(f"Mais simples entre as empatadas: {escolhido.f1_medio:.4f}  {escolhido.candidato.descrever()}")

    destino = escrever_relatorio_do_ajuste(resultados, escolhido, args.dataset, args.k, origem)
    print(f"\nRelatório salvo em:\n  {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
