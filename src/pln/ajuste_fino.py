# =============================================================================
# ajuste_fino.py — Busca dos hiperparâmetros do MODELO DO PRODUTO
# =============================================================================
# O que este script responde, com número em vez de opinião:
#
# 1. Qual variante de Naive Bayes classifica melhor estas intenções?
# 2. Quanta suavização (`alpha`) é a certa para este vocabulário?
# 3. As probabilidades a priori devem vir do treino (`fit_prior`) ou ser
#    uniformes?
# 4. Sob os melhores pré-processamentos, qual vetorização o modelo final
#    prefere — sabendo que ela pode não ser a que a régua do experimento preferiu?
#
# A DIVISÃO DE TRABALHO COM experimento.py
# ----------------------------------------
# São duas perguntas diferentes, e cada script fixa o que o outro varia:
#
#     experimento.py  varia  o texto      (pré-processamento x vetorização)
#                     fixa   o modelo     MultinomialNB(alpha=1.0), a régua
#
#     ajuste_fino.py  varia  o modelo     (variante x suavização x priori)
#                     fixa   o texto      os melhores do experimento
#
# ISSO É UMA BUSCA EM ESTÁGIOS, E ESTÁGIO NÃO ACHA ÓTIMO GLOBAL — a mesma
# objeção que fez a opção `--duas-fases` ser removida de `experimento.py`. A
# diferença que justifica manter aqui é de tamanho, não de método: o produto
# cartesiano completo seria 432 pré-processamentos x 5 vetorizações x variantes
# x 6 valores de suavização x 2 prioris, na casa das dezenas de milhares de
# validações cruzadas. O corte está declarado e é ajustável em uma flag
# (`--top-pre`, e `--top-pre 0` varre TODOS os pré-processamentos do relatório).
#
# De onde vêm os candidatos de texto: do CSV que `experimento.py` grava. Rode o
# experimento primeiro. Sem o arquivo, este script cai numa lista mínima embutida
# e avisa que está fazendo isso.
#
# USO
# ---
#     python -m pln.experimento          # primeiro, para gerar os candidatos
#     python -m pln.ajuste_fino          # depois, para ajustar o modelo
#     python -m pln.ajuste_fino --top-pre 20 --k 10
#     python -m pln.ajuste_fino --top-pre 0     # todos os pré-processamentos
# =============================================================================

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
from pln.classificador import (
    VarianteNB,
    carregar_dataset,
    construir_classificador,
    variantes_compativeis,
)
from pln.preprocessamento import (
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
)
from pln.vetorizacao import ConfigVetorizacao, todas_as_vetorizacoes

SEMENTE = 42
LARGURA = 118

# A suavização das variantes de contagem. Abaixo de 1,0 o modelo confia mais nas
# contagens observadas; acima, puxa tudo para a uniforme e apaga as diferenças
# entre classes. O padrão do scikit-learn é 1,0.
GRADE_ALPHA: tuple[float, ...] = (0.01, 0.05, 0.1, 0.5, 1.0, 2.0)

# A suavização da variante gaussiana vive em outra escala inteiramente: é uma
# fração da maior variância, somada a todas as variâncias para estabilizar a
# divisão. O padrão do scikit-learn é 1e-9. Usar aqui a grade de `alpha` seria
# testar seis valores igualmente destrutivos.
GRADE_VAR_SMOOTHING: tuple[float, ...] = (1e-11, 1e-9, 1e-7, 1e-5, 1e-3, 1e-1)

# `fit_prior=False` fixa as prioris em uniformes — o análogo mais próximo do
# `class_weight="balanced"` que Naive Bayes não tem. Só se aplica às variantes
# de contagem.
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
    variante: VarianteNB
    suavizacao: float
    fit_prior: bool

    def descrever(self) -> str:
        priori = "" if self.variante is VarianteNB.GAUSSIANO else f" prior={'treino' if self.fit_prior else 'unif'}"
        return (
            f"{self.variante.value:>11} s={self.suavizacao:<7g}{priori} | "
            f"{self.config_vet.descrever()} | {self.config_pre.descrever()}"
        )


# O nome carrega o "DoAjuste" porque `experimento.py` tem o seu próprio
# `Resultado`, com outros campos. Enquanto são módulos separados os dois nomes
# curtos conviveriam; no arquivo único de `entregas/`, o segundo apagaria o
# primeiro em silêncio. O gerador recusa a junção quando isso acontece, e a
# saída dele foi o que motivou este nome.
@dataclass
class ResultadoDoAjuste:
    candidato: Candidato
    f1_medio: float
    f1_desvio: float


# -----------------------------------------------------------------------------
# Os candidatos de texto, lidos do relatório do experimento
# -----------------------------------------------------------------------------


# Reconstrói uma `ConfigPreprocessamento` a partir de uma linha do CSV.
#
# O CSV grava cada campo em coluna própria justamente para permitir isto — ler
# de volta sem precisar interpretar a string de descrição, que é para humano.
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


# Os melhores pré-processamentos distintos do relatório, na ordem do ranking.
#
# Distintos importa: o CSV tem uma linha por (pré-processamento, vetorização),
# então o mesmo texto aparece até cinco vezes seguidas no topo. Sem a
# deduplicação, `--top-pre 5` traria um único pré-processamento cinco vezes.
def carregar_candidatos_de_texto(quantos: int) -> tuple[list[ConfigPreprocessamento], str]:
    caminho = dir_resultados() / "comparativo_preprocessamento.csv"
    if not caminho.is_file():
        return list(PRE_PROCESSAMENTOS_DE_EMERGENCIA), (
            f"⚠️  {caminho.name} não encontrado — usando a lista mínima embutida.\n"
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


# -----------------------------------------------------------------------------
# O espaço de busca do modelo
# -----------------------------------------------------------------------------


# A grade de suavização depende da variante — ver o comentário das constantes.
def grade_de_suavizacao(variante: VarianteNB) -> tuple[float, ...]:
    return GRADE_VAR_SMOOTHING if variante is VarianteNB.GAUSSIANO else GRADE_ALPHA


# GaussianNB não tem `fit_prior`; varrer os dois valores geraria duas linhas
# idênticas com nomes diferentes, o que é pior do que não varrer.
def grade_de_prior(variante: VarianteNB) -> tuple[bool, ...]:
    return (True,) if variante is VarianteNB.GAUSSIANO else GRADE_FIT_PRIOR


def montar_candidatos(configs_pre: list[ConfigPreprocessamento]) -> list[Candidato]:
    candidatos: list[Candidato] = []
    for config_pre, config_vet in itertools.product(configs_pre, todas_as_vetorizacoes()):
        for variante in variantes_compativeis(config_vet):
            for suavizacao, fit_prior in itertools.product(
                grade_de_suavizacao(variante), grade_de_prior(variante)
            ):
                candidatos.append(Candidato(config_pre, config_vet, variante, suavizacao, fit_prior))
    return candidatos


# Mede um candidato por validação cruzada estratificada.
#
# O pré-processamento é etapa do Pipeline, então ele é reaplicado dentro de cada
# dobra. Custa tempo e é o certo: mantém a garantia de que nada aprendido no
# treino vaza para o teste, e é a mesma disciplina do experimento.
def medir(candidato: Candidato, textos: list[str], rotulos: list[str], k: int) -> ResultadoDoAjuste:
    modelo = construir_classificador(
        config_pre=candidato.config_pre,
        config_vet=candidato.config_vet,
        variante=candidato.variante,
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


# -----------------------------------------------------------------------------
# Análise
# -----------------------------------------------------------------------------


# O ESPAÇO DE BUSCA TEM DUAS REGIÕES DISJUNTAS, E ISSO MUDA COMO SE COMPARA
# --------------------------------------------------------------------------
# `gaussiano` só existe com vetorização densa; as outras três variantes só
# existem com esparsa. As grades de suavização também são disjuntas — `alpha`
# perto de 1, `var_smoothing` perto de 1e-9.
#
# Uma comparação pareada exige que os grupos comparados sejam completos. Se o
# universo for o espaço inteiro, NENHUM grupo é completo: nenhuma combinação tem
# todas as variantes, porque não pode ter. A primeira versão desta função
# ignorava isso, e o efeito foi a tabela de variante, de suavização e de
# vetorização SUMIREM do relatório sem erro nenhum — exatamente o mesmo defeito
# que `medir_efeito_da_vetorizacao` tinha em experimento.py.
#
# A correção é comparar DENTRO de cada região. Cada tabela sai rotulada com a
# região a que se refere, e comparar as duas entre si é uma pergunta diferente,
# respondida na linha "esparsa vs densa" da recomendação.
def separar_por_familia(resultados: list[ResultadoDoAjuste]) -> list[tuple[str, list[ResultadoDoAjuste]]]:
    esparsos = [r for r in resultados if not r.candidato.config_vet.produz_vetores_densos()]
    densos = [r for r in resultados if r.candidato.config_vet.produz_vetores_densos()]
    return [(nome, grupo) for nome, grupo in (("esparsa", esparsos), ("densa", densos)) if grupo]


# Como cada valor de eixo aparece nas tabelas. Os três tipos que circulam aqui
# imprimem de formas diferentes, e o `str()` cru de um dataclass é ilegível:
# "ConfigVetorizacao(modo=<ModoVetorizacao.TFIDF: 'tfidf'>, n_max=2)" no lugar de
# "tfidf n=1-2".
def rotular(valor) -> str:
    if hasattr(valor, "descrever"):
        return valor.descrever()
    if hasattr(valor, "value"):
        return str(valor.value)
    return str(valor)


# O efeito de um eixo dentro de UMA região, comparado de forma PAREADA: para
# cada combinação dos outros eixos, compara os valores deste entre si.
#
# Média solta não serve: ela compararia amostras diferentes e atribuiria ao eixo
# uma diferença que veio do resto.
def comparar_eixo(resultados: list[ResultadoDoAjuste], eixo: str) -> list[tuple[str, float, int]]:
    outros = [c for c in ("config_pre", "config_vet", "variante", "suavizacao", "fit_prior") if c != eixo]

    grupos: dict[tuple, dict[str, float]] = {}
    for resultado in resultados:
        chave = tuple(getattr(resultado.candidato, campo) for campo in outros)
        grupos.setdefault(chave, {})[rotular(getattr(resultado.candidato, eixo))] = resultado.f1_medio

    rotulos = {r for g in grupos.values() for r in g}
    if len(rotulos) < 2:
        return []  # eixo constante nesta região: não há o que comparar

    completos = [g for g in grupos.values() if len(g) == len(rotulos)]
    if not completos:
        return []

    return sorted(
        ((rotulo, statistics.mean(g[rotulo] for g in completos), len(completos)) for rotulo in rotulos),
        key=lambda linha: linha[1],
        reverse=True,
    )


# A melhor de cada região, para a pergunta que a comparação pareada não responde:
# vale a pena a vetorização densa?
#
# Aqui a comparação é entre os TOPOS, não entre médias, e de propósito. A média
# de uma região inteira mistura combinações boas e absurdas — `var_smoothing=1e-1`
# arrasa a região densa e puxaria a média para baixo por um motivo que não é a
# representação. O que interessa para decidir é o melhor que cada uma alcança.
def melhor_por_familia(resultados: list[ResultadoDoAjuste]) -> list[tuple[str, ResultadoDoAjuste]]:
    return [(nome, max(grupo, key=lambda r: r.f1_medio)) for nome, grupo in separar_por_familia(resultados)]


# Entre as configurações empatadas com a melhor, a mais simples.
#
# Empate aqui é "dentro de um desvio padrão da melhor" — a mesma régua do
# experimento. Simplicidade é, em ordem: menos etapas de pré-processamento,
# vetorização esparsa antes de densa (não depende de baixar modelo de 40 MB), e
# suavização mais próxima do padrão da biblioteca.
def escolher_mais_simples(resultados: list[ResultadoDoAjuste]) -> ResultadoDoAjuste:
    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatados = [r for r in resultados if r.f1_medio >= limiar]

    def custo(r: ResultadoDoAjuste) -> tuple:
        c = r.candidato
        padrao = 1e-9 if c.variante is VarianteNB.GAUSSIANO else 1.0
        return (
            len(c.config_pre.etapas_ativas_na_ordem()),
            c.config_vet.produz_vetores_densos(),
            c.config_vet.n_max,
            abs(c.suavizacao - padrao),
            -r.f1_medio,
        )

    return min(empatados, key=custo)


# -----------------------------------------------------------------------------
# Saída
# -----------------------------------------------------------------------------


# `descrever()` usa `|` como separador, e `|` é o que delimita coluna em tabela
# markdown. Sem escapar, uma configuração vira três colunas e a tabela inteira
# se desalinha a partir dali.
def escapar_para_tabela(texto: str) -> str:
    return texto.replace("|", "\\|")


# O bloco de valores prontos para colar em `classificador.py`.
#
# Precisa ser Python VÁLIDO. O `repr()` de um dataclass com enums não é: ele
# imprime `<ModoStopwords.MANTER: 'manter'>`, que não compila, além de listar
# todos os campos no valor padrão. O que sai daqui é o construtor mínimo — só os
# campos que diferem do padrão — e é copiável direto.
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
    # A tokenização entra sempre: é decisão registrada, não omissão.
    argumentos.append(f"tokenizacao=Tokenizacao.{candidato.config_pre.tokenizacao.name}")

    fit_prior = "" if candidato.variante is VarianteNB.GAUSSIANO else f"\nFIT_PRIOR_PADRAO  = {candidato.fit_prior}"
    return [
        "```python",
        f"CONFIG_PRE_PADRAO = ConfigPreprocessamento({', '.join(argumentos)})",
        f"CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.{candidato.config_vet.modo.name}, "
        f"n_max={candidato.config_vet.n_max})",
        f"VARIANTE_PADRAO   = VarianteNB.{candidato.variante.name}",
        f"ALPHA_PADRAO      = {candidato.suavizacao!r}" + fit_prior,
        "```",
    ]

EIXOS_ANALISADOS = ("variante", "suavizacao", "fit_prior", "config_vet")

TITULOS_DOS_EIXOS = {
    "variante": "VARIANTE DE NAIVE BAYES",
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
    for familia, grupo in separar_por_familia(resultados):
        for eixo in EIXOS_ANALISADOS:
            linhas = comparar_eixo(grupo, eixo)
            if not linhas:
                continue
            cabecalho = (f"{TITULOS_DOS_EIXOS[eixo]} — vetorização {familia}, "
                         f"pareado em {linhas[0][2]} combinações")
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
        "### Esparsa contra densa",
        "",
        "O melhor que cada família de vetorização alcança — a comparação que as tabelas",
        "pareadas abaixo não fazem, porque elas comparam DENTRO de cada família.",
        "",
        "| vetorização | melhor F1 | configuração |",
        "|---|---|---|",
        *(f"| {nome} | {topo.f1_medio:.4f} | `{escapar_para_tabela(topo.candidato.descrever())}` |"
          for nome, topo in melhor_por_familia(resultados)),
        "",
        "Valores para `classificador.py`:",
        "",
        *gerar_bloco_de_configuracao(escolhido.candidato),
    ]

    for familia, grupo in separar_por_familia(resultados):
        for eixo in EIXOS_ANALISADOS:
            comparacao = comparar_eixo(grupo, eixo)
            if not comparacao:
                continue
            linhas += [
                "", f"## {TITULOS_DOS_EIXOS[eixo].capitalize()} — vetorização {familia}", "",
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
    print()
    for nome, topo in melhor_por_familia(resultados):
        print(f"Melhor com vetorização {nome:>8}: {topo.f1_medio:.4f}  {topo.candidato.descrever()}")

    destino = escrever_relatorio_do_ajuste(resultados, escolhido, args.dataset, args.k, origem)
    print(f"\nRelatório salvo em:\n  {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
