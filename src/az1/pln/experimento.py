"""
experimento.py — Busca em duas fases pela melhor configuração do pipeline.

O que este script responde, com número em vez de opinião:

1. Quais etapas de pré-processamento ajudam neste dataset?
2. A ORDEM das etapas importa? A ordem padrão é a melhor?
3. Remover stopwords ajuda? E remover preservando as negações?
4. Stemming ou lematização — qual reduz melhor as palavras?
5. Qual estratégia de tokenização produz o melhor vocabulário?
6. Sobre o melhor pré-processamento, qual vetorização e qual janela de n-grama?

MÉTODO PADRÃO: VARREDURA EXAUSTIVA
-----------------------------------
Por padrão o experimento testa o produto cartesiano completo — cada
pré-processamento contra cada vetorização. É o único método que encontra o
ótimo global, e no nosso tamanho de dataset custa alguns minutos.

A alternativa `--duas-fases` faz uma busca em estágios: varre o
pré-processamento com a vetorização fixa, seleciona as melhores configurações e
só então varre a vetorização sobre elas. Custa 4x menos.

    FASE 1  varre o pré-processamento com a vetorização FIXA
                          |
                          v
            seleciona as melhores configurações
                          |
                          v
    FASE 2  varre a vetorização sobre essas configurações

POR QUE ELA NÃO É O PADRÃO — busca em estágios não garante o ótimo global, e
neste dataset comprovadamente não o encontra. O melhor pré-processamento sob
TF-IDF não é o melhor sob bag-of-words: `remover_numeros` é medíocre sob a
régua TF-IDF (79º lugar na Fase 1) e é a melhor configuração sob bag-of-words.
A busca em estágios perde essa combinação por 0,0078 de F1.

O modo em duas fases continua útil quando a varredura completa ficar cara —
dataset grande, muitas dobras, ou um espaço de busca ampliado. Nesses casos,
`--top-fase1` alto reduz a chance de perder o ótimo.

O espaço de busca do pré-processamento:

    4 etapas booleanas (minúsculas, acentos, pontuação, números) -> 2^4 = 16
    3 modos de stopwords (manter / remover tudo / preservar não) ->       3
    3 modos de morfologia (nenhuma / stemming / lematização)     ->       3
    3 tokenizações (split / regex / linguística)                 ->       3
                                                                    ---------
    configurações                                                ->     432

    para cada uma, TODAS as permutações das etapas ativas        ->  19.767

Ordens que produzem TEXTO IDÊNTICO são o mesmo experimento e são deduplicadas.

Uso:

    python -m az1.pln.experimento                    # varredura exaustiva (padrão)
    python -m az1.pln.experimento --dataset caminho/seus_dados.csv --k 10
    python -m az1.pln.experimento --sem-ordem        # só a ordem padrão
    python -m az1.pln.experimento --duas-fases       # busca em estágios, 4x mais rápida
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_validate

from az1.pln.preprocessamento import (
    ETAPAS,
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
    preprocessar,
)
from az1.pln.vetorizacao import (
    VETORIZACAO_REFERENCIA,
    ConfigVetorizacao,
    ModoVetorizacao,
    construir_pipeline,
    todas_as_vetorizacoes,
)

DADOS_PADRAO = Path(__file__).resolve().parent / "dados" / "intencoes_exemplo.csv"
RESULTADOS_DIR = Path(__file__).resolve().parent / "resultados"

# Semente fixa. Sem ela, as dobras da validação cruzada mudariam a cada
# execução e duas configurações não seriam comparáveis: parte da diferença
# entre elas seria sorteio diferente, não pré-processamento diferente.
SEMENTE = 42

#: Campos categóricos da configuração. Cada um vira uma comparação pareada.
#: O primeiro valor de cada enum é a referência ("não fazer nada").
CATEGORICOS: tuple[tuple[str, type[StrEnum]], ...] = (
    ("stopwords", ModoStopwords),
    ("morfologia", ModoMorfologia),
    ("tokenizacao", Tokenizacao),
)

#: Campos que identificam uma configuração, usados para parear comparações.
CAMPOS_CONFIG: tuple[str, ...] = (
    "minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros",
    "stopwords", "morfologia", "tokenizacao",
)

LARGURA = 118


@dataclass(frozen=True)
class Resultado:
    config: ConfigPreprocessamento
    vetorizacao: ConfigVetorizacao
    f1_medio: float
    f1_desvio: float
    tamanho_vocabulario: float
    ordens_equivalentes: int = 1
    e_ordem_padrao: bool = True

    @property
    def chave_etapas(self) -> ConfigPreprocessamento:
        """A configuração sem a ordem — usada para agrupar as ordens irmãs."""
        return self.config.com_ordem(ETAPAS)

    def chave_relatorio(self) -> str:
        return f"{self.vetorizacao.rotulo()} | {self.config.rotulo()}"


def avaliar(
    textos: list[str], rotulos: list[str], vetorizacao: ConfigVetorizacao, k: int
) -> tuple[float, float, float]:
    """Validação cruzada estratificada. Devolve (F1 médio, desvio, vocab médio).

    Validação cruzada e não uma divisão única porque, com poucas centenas de
    exemplos, uma divisão só daria uma nota dependente demais de quais frases
    caíram no teste — trocando a semente, a "melhor" configuração mudaria.

    ESTRATIFICADA para que cada dobra tenha as três intenções na mesma
    proporção; sem isso uma dobra poderia sair sem nenhum "alerta" e o F1
    daquela classe ficaria indefinido.

    F1-macro e não acurácia porque acurácia engana com classes desbalanceadas:
    se 80% fossem consulta, responder "consulta" para tudo daria 80% e seria
    inútil. O macro tira média por classe, então a rara pesa igual à comum.
    """
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    saida = cross_validate(
        construir_pipeline(vetorizacao),
        textos,
        rotulos,
        cv=dobras,
        scoring="f1_macro",
        return_estimator=True,
    )
    scores = list(saida["test_score"])
    vocabs = [len(e.named_steps["vetorizador"].vocabulary_) for e in saida["estimator"]]
    desvio = statistics.stdev(scores) if len(scores) > 1 else 0.0
    return statistics.mean(scores), desvio, statistics.mean(vocabs)


# ---------------------------------------------------------------------------
# Fase 1 — pré-processamento, com a vetorização fixa
# ---------------------------------------------------------------------------


def configuracoes_de_etapas() -> list[ConfigPreprocessamento]:
    """As 432 configurações, todas com a ordem padrão.

    Produto cartesiano de 4 booleanas x 3 modos de stopwords x 3 modos de
    morfologia x 3 tokenizações. As permutações de ordem entram depois, por
    configuração, em `ordens_a_testar`.
    """
    combos = []
    for mi, ra, rp, rn in itertools.product([False, True], repeat=4):
        for sw, mo, tk in itertools.product(ModoStopwords, ModoMorfologia, Tokenizacao):
            combos.append(
                ConfigPreprocessamento(
                    minusculas=mi, remover_acentos=ra, remover_pontuacao=rp,
                    remover_numeros=rn, stopwords=sw, morfologia=mo, tokenizacao=tk,
                )
            )
    return combos


def ordens_a_testar(base: ConfigPreprocessamento, variar_ordem: bool) -> list[tuple[str, ...]]:
    """As ordens a experimentar para uma configuração de etapas.

    Só as etapas ATIVAS são permutadas — permutar uma etapa desligada não muda
    nada e multiplicaria o custo à toa. As desligadas são acrescentadas ao fim,
    na ordem padrão, apenas para satisfazer a validação do dataclass.
    """
    ativas = base.etapas_ativas()
    if not variar_ordem:
        return [base.ordem]

    inativas = tuple(e for e in ETAPAS if e not in ativas)
    return [perm + inativas for perm in itertools.permutations(ativas)]


def _digest(corpus: tuple[str, ...]) -> str:
    return hashlib.blake2b("\n".join(corpus).encode("utf-8"), digest_size=16).hexdigest()


def varrer(
    textos: list[str],
    rotulos: list[str],
    k: int,
    variar_ordem: bool,
    vetorizacoes: list[ConfigVetorizacao],
) -> tuple[list[Resultado], int]:
    """Varre o pré-processamento e devolve (resultados, permutações examinadas).

    Por padrão `vetorizacoes` traz as quatro, e o resultado é o produto
    cartesiano completo. Com `--duas-fases` traz só a régua, e esta função
    passa a ser a Fase 1.
    """
    resultados: list[Resultado] = []
    permutacoes = 0
    bases = configuracoes_de_etapas()

    for numero, base in enumerate(bases, start=1):
        ativas = base.etapas_ativas()
        ordem_padrao = tuple(e for e in ETAPAS if e in ativas) + tuple(
            e for e in ETAPAS if e not in ativas
        )

        # digest -> [config representante, corpus, nº de ordens equivalentes, contém a ordem padrão]
        distintos: dict[str, list] = {}
        for ordem in ordens_a_testar(base, variar_ordem):
            permutacoes += 1
            config = base.com_ordem(ordem)
            corpus = tuple(preprocessar(t, config) for t in textos)
            chave = _digest(corpus)

            if chave in distintos:
                distintos[chave][2] += 1
                distintos[chave][3] = distintos[chave][3] or (ordem == ordem_padrao)
            else:
                distintos[chave] = [config, list(corpus), 1, ordem == ordem_padrao]

        for config, corpus, equivalentes, tem_padrao in distintos.values():
            for vetorizacao in vetorizacoes:
                media, desvio, vocab = avaliar(corpus, rotulos, vetorizacao, k)
                resultados.append(
                    Resultado(config, vetorizacao, media, desvio, vocab, equivalentes, tem_padrao)
                )

        if sys.stdout.isatty():
            print(f"\r  {numero}/{len(bases)} configurações de pré-processamento", end="", flush=True)

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados, permutacoes


def selecionar_melhores(resultados: list[Resultado], quantas: int) -> list[ConfigPreprocessamento]:
    """As configurações que passam para a Fase 2.

    São as `quantas` melhores por F1, mais duas de controle que entram sempre,
    ainda que não estejam no topo:

    - a MAIS SIMPLES entre as empatadas com a primeira (dentro de um desvio
      padrão). Se ela vencer na Fase 2 também, adotamos menos etapas pelo mesmo
      resultado;
    - o TEXTO CRU com tokenização simples, como linha de base. Sem ele não há
      como afirmar que o pré-processamento agregou alguma coisa.

    Configurações repetidas são descartadas — a mesma configuração pode
    aparecer mais de uma vez no ranking sob ordens diferentes que produziram
    textos diferentes.
    """
    escolhidas: list[ConfigPreprocessamento] = []
    vistas: set[ConfigPreprocessamento] = set()

    def acrescentar(config: ConfigPreprocessamento) -> None:
        if config not in vistas:
            vistas.add(config)
            escolhidas.append(config)

    for r in resultados[:quantas]:
        acrescentar(r.config)

    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatadas = [r for r in resultados if r.f1_medio >= limiar]
    if empatadas:
        acrescentar(min(empatadas, key=lambda r: (len(r.config.etapas_ativas()), -r.f1_medio)).config)

    acrescentar(ConfigPreprocessamento())
    return escolhidas


# ---------------------------------------------------------------------------
# Fase 2 — vetorização, sobre os melhores pré-processamentos
# ---------------------------------------------------------------------------


def fase2(
    textos: list[str],
    rotulos: list[str],
    selecionadas: list[ConfigPreprocessamento],
    k: int,
) -> list[Resultado]:
    """Testa todas as vetorizações sobre cada configuração selecionada.

    Aqui o texto é a constante e a vetorização é a variável — o inverso exato
    da Fase 1. Como as configurações vieram prontas, o corpus é recalculado uma
    vez por configuração e reaproveitado nas quatro vetorizações.
    """
    resultados: list[Resultado] = []
    vetorizacoes = todas_as_vetorizacoes()

    for numero, config in enumerate(selecionadas, start=1):
        corpus = [preprocessar(t, config) for t in textos]
        for vetorizacao in vetorizacoes:
            media, desvio, vocab = avaliar(corpus, rotulos, vetorizacao, k)
            resultados.append(Resultado(config, vetorizacao, media, desvio, vocab))

        if sys.stdout.isatty():
            print(f"\r  Fase 2: {numero}/{len(selecionadas)} configurações", end="", flush=True)

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados


def efeito_da_vetorizacao(resultados: list[Resultado]) -> list[tuple[str, float, float, int]]:
    """Efeito de cada escolha de vetorização, PAREADO por pré-processamento.

    Cada configuração selecionada foi avaliada sob as quatro vetorizações, e
    são exatamente esses quartetos que se comparam entre si. Como o texto é
    idêntico dentro de cada quarteto, a diferença só pode vir da vetorização.
    """
    por_config: dict[ConfigPreprocessamento, dict[ConfigVetorizacao, float]] = defaultdict(dict)
    for r in resultados:
        por_config[r.config][r.vetorizacao] = r.f1_medio

    completos = [d for d in por_config.values() if len(d) == 4]
    if not completos:
        return []

    linhas: list[tuple[str, float, float, int]] = []
    for nome, pertence in (
        ("tfidf (vs bow)", lambda v: v.modo is ModoVetorizacao.TFIDF),
        ("bigrama (vs só uni)", lambda v: v.n_max >= 2),
    ):
        com = [statistics.mean(f for v, f in d.items() if pertence(v)) for d in completos]
        sem = [statistics.mean(f for v, f in d.items() if not pertence(v)) for d in completos]
        linhas.append((nome, statistics.mean(com), statistics.mean(sem), len(completos)))

    return sorted(linhas, key=lambda linha: linha[1] - linha[2], reverse=True)


# ---------------------------------------------------------------------------
# Análises da Fase 1
# ---------------------------------------------------------------------------


def efeito_das_escolhas_binarias(resultados: list[Resultado]) -> list[tuple[str, float, float, float]]:
    """Efeito médio de cada etapa booleana, sobre TODAS as execuções da fase.

    Esta é a leitura confiável, e não o topo do ranking. Com poucos dados, a
    combinação em primeiro lugar chegou lá em boa parte por sorteio — o desvio
    padrão costuma ser maior que a diferença entre as dez primeiras.

    Aqui cada média resume metade do espaço de busca, então o ruído das outras
    escolhas se cancela e o que sobra é o efeito daquela etapa isolada.
    """
    linhas: list[tuple[str, float, float, float]] = []
    for flag in ("minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros"):
        com = [r.f1_medio for r in resultados if getattr(r.config, flag)]
        sem = [r.f1_medio for r in resultados if not getattr(r.config, flag)]
        media_com, media_sem = statistics.mean(com), statistics.mean(sem)
        linhas.append((flag, media_com, media_sem, media_com - media_sem))

    return sorted(linhas, key=lambda linha: linha[3], reverse=True)


def comparacao_pareada(
    resultados: list[Resultado], campo: str, enum_: type[StrEnum]
) -> tuple[list[tuple[str, float, float]], int]:
    """Compara os valores de um campo categórico, PAREADO.

    Vale para os três campos de múltipla escolha: tratamento de stopwords,
    normalização morfológica e tokenização.

    POR QUE PAREADO, E NÃO A MÉDIA SIMPLES
    ---------------------------------------
    Média simples por valor seria enviesada. Quando stopwords é `manter`, ou
    morfologia é `nenhuma`, a etapa correspondente não entra na lista de etapas
    ativas — a configuração fica com UMA ETAPA A MENOS e, portanto, com menos
    permutações de ordem. Comparar essa média com a dos demais valores
    misturaria dois efeitos: o do tratamento em si e o de ter menos etapas.

    O pareamento resolve: para cada conjunto idêntico das demais escolhas
    (mesmas etapas, mesmos outros campos categóricos, mesma vetorização, todos
    na ordem padrão), pegam-se todos os valores do campo e comparam-se entre
    si. Tudo o mais constante — a diferença só pode vir do campo em questão.

    A referência é o PRIMEIRO valor do enum, que é sempre o "não fazer nada":
    manter as stopwords, nenhuma morfologia, tokenizar só por espaço.
    """
    outros = tuple(c for c in CAMPOS_CONFIG if c != campo)
    pares: dict[tuple, dict[StrEnum, float]] = defaultdict(dict)

    for r in resultados:
        if not r.e_ordem_padrao:
            continue
        chave = tuple(getattr(r.config, c) for c in outros) + (r.vetorizacao,)
        pares[chave][getattr(r.config, campo)] = r.f1_medio

    valores = list(enum_)
    completos = [d for d in pares.values() if len(d) == len(valores)]
    if not completos:
        return [], 0

    referencia = statistics.mean(d[valores[0]] for d in completos)
    linhas = [
        (v.value, statistics.mean(d[v] for d in completos), statistics.mean(d[v] for d in completos) - referencia)
        for v in valores
    ]
    return linhas, len(completos)


@dataclass
class AnaliseDeOrdem:
    grupos_sensiveis: int
    grupos_totais: int
    amplitude_media: float
    amplitude_maxima: float
    pior_caso: tuple[Resultado, Resultado] | None
    padrao_venceu: int
    padrao_avaliado: int
    perda_media_do_padrao: float


def analisar_ordem(resultados: list[Resultado]) -> AnaliseDeOrdem:
    """Responde: a ordem importa, e a ordem padrão é a melhor?

    Um GRUPO é o conjunto de resultados que compartilham exatamente as mesmas
    etapas e a mesma vetorização, diferindo APENAS na ordem. Dentro de um
    grupo, tudo o mais é constante — então qualquer diferença de F1 só pode ter
    vindo da ordem. É um experimento controlado, e é o que dá direito de
    afirmar causa em vez de correlação.

    A amplitude do grupo (maior F1 menos menor F1) é o tamanho do efeito da
    ordem naquela configuração.
    """
    grupos: dict[tuple, list[Resultado]] = defaultdict(list)
    for r in resultados:
        grupos[(r.chave_etapas, r.vetorizacao)].append(r)

    amplitudes: list[float] = []
    pior_caso = None
    amplitude_maxima = 0.0
    padrao_venceu = padrao_avaliado = 0
    perdas: list[float] = []

    for membros in grupos.values():
        if len(membros) < 2:
            continue

        melhor = max(membros, key=lambda r: r.f1_medio)
        pior = min(membros, key=lambda r: r.f1_medio)
        amplitude = melhor.f1_medio - pior.f1_medio
        amplitudes.append(amplitude)

        if amplitude > amplitude_maxima:
            amplitude_maxima, pior_caso = amplitude, (melhor, pior)

        padrao = next((r for r in membros if r.e_ordem_padrao), None)
        if padrao is not None:
            padrao_avaliado += 1
            perdas.append(melhor.f1_medio - padrao.f1_medio)
            if padrao.f1_medio >= melhor.f1_medio - 1e-12:
                padrao_venceu += 1

    return AnaliseDeOrdem(
        grupos_sensiveis=len(amplitudes),
        grupos_totais=len(grupos),
        amplitude_media=statistics.mean(amplitudes) if amplitudes else 0.0,
        amplitude_maxima=amplitude_maxima,
        pior_caso=pior_caso,
        padrao_venceu=padrao_venceu,
        padrao_avaliado=padrao_avaliado,
        perda_media_do_padrao=statistics.mean(perdas) if perdas else 0.0,
    )


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------


def _ranking(resultados: list[Resultado], top: int) -> None:
    print(f"{'#':>3}  {'F1-macro':>8}  {'±dp':>6}  {'vocab':>6}  combinação")
    print("-" * LARGURA)
    for posicao, r in enumerate(resultados[:top], start=1):
        print(
            f"{posicao:>3}  {r.f1_medio:>8.4f}  {r.f1_desvio:>6.4f}  "
            f"{r.tamanho_vocabulario:>6.0f}  {r.chave_relatorio()}"
        )
    pior = resultados[-1]
    print("-" * LARGURA)
    print(f"pior  {pior.f1_medio:>7.4f}  {pior.f1_desvio:>6.4f}  {pior.tamanho_vocabulario:>6.0f}  {pior.chave_relatorio()}")


def imprimir_varredura(
    resultados: list[Resultado], top: int, permutacoes: int, variar_ordem: bool, duas_fases: bool
) -> None:
    titulo = (
        "FASE 1 — PRÉ-PROCESSAMENTO (vetorização fixa como régua)"
        if duas_fases
        else "VARREDURA EXAUSTIVA — pré-processamento x vetorização"
    )
    print(f"\n{'=' * LARGURA}")
    print(f"{titulo:^{LARGURA}}")
    print("=" * LARGURA)
    _ranking(resultados, top)

    print(f"\n{'EFEITO DE CADA ETAPA BOOLEANA':^{LARGURA}}")
    print(f"{'etapa':>24}  {'com':>8}  {'sem':>10}  {'efeito':>9}")
    print("-" * LARGURA)
    for nome, com, sem, efeito in efeito_das_escolhas_binarias(resultados):
        marca = "  <- atrapalha" if efeito < -0.01 else ("  <- ajuda" if efeito > 0.01 else "")
        print(f"{nome:>24}  {com:>8.4f}  {sem:>10.4f}  {efeito:>+9.4f}{marca}")

    titulos = {
        "stopwords": "TRATAMENTO DE STOPWORDS",
        "morfologia": "NORMALIZAÇÃO MORFOLÓGICA — stemming contra lematização",
        "tokenizacao": "ESTRATÉGIA DE TOKENIZAÇÃO",
    }
    for campo, enum_ in CATEGORICOS:
        linhas_campo, pares = comparacao_pareada(resultados, campo, enum_)
        cabecalho = f"{titulos[campo]} — pareado em {pares} configurações"
        print(f"\n{cabecalho:^{LARGURA}}")
        print(f"{'opção':>24}  {'F1 médio':>8}  {'vs ' + list(enum_)[0].value:>22}")
        print("-" * LARGURA)
        for valor, media, delta in linhas_campo:
            print(f"{valor:>24}  {media:>8.4f}  {delta:>+22.4f}")
        if campo == "stopwords" and len(linhas_campo) == 3:
            ganho = linhas_campo[2][1] - linhas_campo[1][1]
            print(f"{'':>24}  preservar as negações recupera {ganho:+.4f} em relação a remover tudo")
        if campo == "morfologia" and len(linhas_campo) == 3:
            diff = linhas_campo[2][1] - linhas_campo[1][1]
            print(f"{'':>24}  {'lematização' if diff > 0 else 'stemming'} leva por {abs(diff):.4f}")

    if variar_ordem:
        o = analisar_ordem(resultados)
        print(f"\n{'A ORDEM IMPORTA?':^{LARGURA}}")
        print("-" * LARGURA)
        print(f"  Permutações examinadas                        : {permutacoes}")
        print(f"  Execuções distintas depois da deduplicação    : {len(resultados)}")
        print(f"  Grupos em que a ordem muda o texto            : {o.grupos_sensiveis} de {o.grupos_totais}")
        print(f"  Amplitude média de F1 dentro desses grupos    : {o.amplitude_media:.4f}")
        print(f"  Amplitude máxima                              : {o.amplitude_maxima:.4f}")
        if o.pior_caso:
            bom, ruim = o.pior_caso
            print(f"    melhor: {bom.f1_medio:.4f}  {bom.chave_relatorio()}")
            print(f"    pior  : {ruim.f1_medio:.4f}  {ruim.chave_relatorio()}")
        if o.padrao_avaliado:
            pct = 100 * o.padrao_venceu / o.padrao_avaliado
            print(f"  Ordem padrão foi a melhor do grupo            : {o.padrao_venceu}/{o.padrao_avaliado} ({pct:.0f}%)")
            print(f"  Perda média por usar a ordem padrão           : {o.perda_media_do_padrao:.4f}")


def imprimir_fase2(
    resultados: list[Resultado], selecionadas: list[ConfigPreprocessamento], top: int
) -> None:
    print(f"\n{'=' * LARGURA}")
    print(f"{'FASE 2 — VETORIZAÇÃO (sobre os melhores pré-processamentos)':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"  Configurações herdadas da Fase 1 : {len(selecionadas)}")
    print(f"  Vetorizações testadas em cada uma: {len(todas_as_vetorizacoes())}")
    print(f"  Execuções desta fase             : {len(resultados)}\n")
    _ranking(resultados, top)

    linhas = efeito_da_vetorizacao(resultados)
    if linhas:
        print(f"\n{f'EFEITO DA VETORIZAÇÃO — pareado em {linhas[0][3]} pré-processamentos':^{LARGURA}}")
        print(f"{'escolha':>24}  {'com':>8}  {'sem':>10}  {'efeito':>9}")
        print("-" * LARGURA)
        for nome, com, sem, _ in linhas:
            efeito = com - sem
            marca = "  <- atrapalha" if efeito < -0.01 else ("  <- ajuda" if efeito > 0.01 else "")
            print(f"{nome:>24}  {com:>8.4f}  {sem:>10.4f}  {efeito:>+9.4f}{marca}")


def imprimir_recomendacao(resultados: list[Resultado]) -> None:
    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatadas = [r for r in resultados if r.f1_medio >= limiar]
    mais_simples = min(
        empatadas, key=lambda r: (len(r.config.etapas_ativas()), r.vetorizacao.n_max, -r.f1_medio)
    )

    print(f"\n{'=' * LARGURA}")
    print(f"{'RECOMENDAÇÃO':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"Melhor absoluta : {melhor.f1_medio:.4f}  {melhor.chave_relatorio()}")
    print(f"Dentro de 1 desvio padrão da melhor: {len(empatadas)} de {len(resultados)} — empatadas na prática.")
    print(f"Mais simples entre as empatadas: {mais_simples.f1_medio:.4f}  {mais_simples.chave_relatorio()}")
    print("\n^ é esta que vale a pena adotar: mesmo resultado, menos etapas para manter.")


def escrever_relatorio(
    principais: list[Resultado],
    fase2_res: list[Resultado],
    selecionadas: list[ConfigPreprocessamento],
    dataset: Path,
    k: int,
    permutacoes: int,
    variar_ordem: bool,
    duas_fases: bool,
) -> None:
    RESULTADOS_DIR.mkdir(exist_ok=True)

    caminho_csv = RESULTADOS_DIR / "comparativo_preprocessamento.csv"
    with caminho_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["fase", "posicao", "f1_macro_medio", "desvio_padrao", "vocabulario_medio", "vetorizador",
             "n_max", "ordem", "ordens_equivalentes", "e_ordem_padrao", "minusculas", "remover_acentos",
             "remover_pontuacao", "remover_numeros", "stopwords", "morfologia", "tokenizacao"]
        )
        for fase, conjunto in (("1", principais), ("2", fase2_res)):
            for posicao, r in enumerate(conjunto, start=1):
                c = r.config
                w.writerow(
                    [fase, posicao, f"{r.f1_medio:.6f}", f"{r.f1_desvio:.6f}",
                     f"{r.tamanho_vocabulario:.1f}", r.vetorizacao.modo.value, r.vetorizacao.n_max,
                     ">".join(c.etapas_ativas()), r.ordens_equivalentes, r.e_ordem_padrao,
                     c.minusculas, c.remover_acentos, c.remover_pontuacao, c.remover_numeros,
                     c.stopwords.value, c.morfologia.value, c.tokenizacao.value]
                )

    linhas = [
        "# Comparativo de pré-processamento e vetorização",
        "",
        f"- Dataset: `{dataset.name}`",
        f"- Validação cruzada estratificada de {k} dobras, semente {SEMENTE}",
        "- Classificador fixo: `MultinomialNB(alpha=1.0)` — régua de medição, não o modelo final",
        "",
        (
            "## Fase 1 — pré-processamento" if duas_fases
            else "## Varredura exaustiva — pré-processamento x vetorização"
        ),
        "",
        (
            f"Vetorização fixa como régua: `{VETORIZACAO_REFERENCIA.rotulo()}`."
            if duas_fases
            else "Produto cartesiano completo: cada pré-processamento contra as "
                 f"{len(todas_as_vetorizacoes())} vetorizações."
        ),
        f"Permutações de ordem examinadas: {permutacoes}. Execuções distintas: {len(principais)}.",
        "",
        "### Efeito de cada etapa booleana",
        "",
        "| etapa | com | sem | efeito |",
        "|---|---|---|---|",
    ]
    for nome, com, sem, efeito in efeito_das_escolhas_binarias(principais):
        linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {efeito:+.4f} |")

    for campo, enum_ in CATEGORICOS:
        linhas_campo, pares = comparacao_pareada(principais, campo, enum_)
        referencia = list(enum_)[0].value
        linhas += [
            "", f"### {campo.capitalize()}", "",
            f"Comparação **pareada** em {pares} configurações idênticas nas demais escolhas.",
            "", f"| opção | F1 médio | vs {referencia} |", "|---|---|---|",
        ]
        for valor, media, delta in linhas_campo:
            linhas.append(f"| {valor} | {media:.4f} | {delta:+.4f} |")

    if variar_ordem:
        o = analisar_ordem(principais)
        linhas += [
            "", "### A ordem importa?", "",
            f"- Grupos em que a ordem muda o texto: **{o.grupos_sensiveis} de {o.grupos_totais}**",
            f"- Amplitude média de F1 nesses grupos: **{o.amplitude_media:.4f}**",
            f"- Amplitude máxima: **{o.amplitude_maxima:.4f}**",
        ]
        if o.padrao_avaliado:
            pct = 100 * o.padrao_venceu / o.padrao_avaliado
            linhas.append(f"- Ordem padrão foi a melhor em **{o.padrao_venceu}/{o.padrao_avaliado} ({pct:.0f}%)** dos grupos")

    if not fase2_res:
        linhas += ["", "### Ranking (top 30)", "",
                   "| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |", "|---|---|---|---|---|---|"]
        for posicao, r in enumerate(principais[:30], start=1):
            linhas.append(
                f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | {r.tamanho_vocabulario:.0f} "
                f"| {r.vetorizacao.rotulo()} | {r.config.rotulo()} |"
            )

    if fase2_res:
        linhas += [
            "", "## Fase 2 — vetorização", "",
            f"{len(selecionadas)} configurações herdadas da Fase 1, cada uma sob "
            f"{len(todas_as_vetorizacoes())} vetorizações.",
            "", "| escolha | com | sem | efeito |", "|---|---|---|---|",
        ]
        for nome, com, sem, _ in efeito_da_vetorizacao(fase2_res):
            linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {com - sem:+.4f} |")

        linhas += ["", "### Ranking final", "",
                   "| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |", "|---|---|---|---|---|---|"]
        for posicao, r in enumerate(fase2_res[:30], start=1):
            linhas.append(
                f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | {r.tamanho_vocabulario:.0f} "
                f"| {r.vetorizacao.rotulo()} | {r.config.rotulo()} |"
            )

    caminho_md = RESULTADOS_DIR / "comparativo_preprocessamento.md"
    caminho_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em:\n  {caminho_csv}\n  {caminho_md}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca em duas fases: pré-processamento, depois vetorização.")
    parser.add_argument("--dataset", type=Path, default=DADOS_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="número de dobras da validação cruzada")
    parser.add_argument("--top", type=int, default=10, help="quantas linhas mostrar em cada ranking")
    parser.add_argument("--sem-ordem", action="store_true", help="usa só a ordem padrão (execução rápida)")
    parser.add_argument("--duas-fases", action="store_true",
                        help="busca em estágios em vez da varredura exaustiva: 4x mais rápida, "
                             "mas pode perder o ótimo global")
    parser.add_argument("--top-fase1", type=int, default=20,
                        help="com --duas-fases: quantas configurações passam para a Fase 2")
    args = parser.parse_args()

    with args.dataset.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    textos = [linha["texto"] for linha in linhas]
    rotulos = [linha["intencao"] for linha in linhas]

    variar_ordem = not args.sem_ordem
    vetorizacoes = [VETORIZACAO_REFERENCIA] if args.duas_fases else todas_as_vetorizacoes()

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Distribuição: {dict(Counter(rotulos))}")
    print(f"Configurações de pré-processamento: {len(configuracoes_de_etapas())}")
    print(f"Varredura de ordem: {'todas as permutações das etapas ativas' if variar_ordem else 'somente a ordem padrão'}")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}")
    if args.duas_fases:
        print(f"Busca em DUAS FASES. Fase 1 com vetorização fixa: {VETORIZACAO_REFERENCIA.rotulo()}")
        print("  (4x mais rápida que a varredura exaustiva, mas pode perder o ótimo global)\n")
    else:
        print(f"Varredura EXAUSTIVA: cada pré-processamento contra as "
              f"{len(vetorizacoes)} vetorizações\n")

    principais, permutacoes = varrer(textos, rotulos, args.k, variar_ordem, vetorizacoes)
    imprimir_varredura(principais, args.top, permutacoes, variar_ordem, args.duas_fases)

    fase2_res: list[Resultado] = []
    selecionadas: list[ConfigPreprocessamento] = []
    if args.duas_fases:
        selecionadas = selecionar_melhores(principais, args.top_fase1)
        fase2_res = fase2(textos, rotulos, selecionadas, args.k)
        imprimir_fase2(fase2_res, selecionadas, args.top)

    imprimir_recomendacao(fase2_res or principais)
    escrever_relatorio(
        principais, fase2_res, selecionadas, args.dataset, args.k, permutacoes, variar_ordem, args.duas_fases
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
