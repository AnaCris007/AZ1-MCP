# Varredura exaustiva do espaço de pré-processamento x vetorização, medida por
# validação cruzada com o classificador fixo (ver `construir_pipeline_de_medicao`).
#
# Espaço: 2^4 etapas booleanas x 3 stopwords x 3 morfologias x 3 tokenizações =
# 432 configurações, cada uma em todas as permutações das suas etapas ativas
# (19.767 no total). Ordens que produzem texto idêntico são deduplicadas.
#
#     python -m pln.experimento
#     python -m pln.experimento --dataset seus_dados.csv --k 10

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from joblib import Parallel, delayed
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from pln.caminhos import DATASET_PADRAO, garantir_dir_de_resultados
from pln.preprocessamento import (
    ETAPAS,
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
    preprocessar,
)
from pln.vetorizacao import (
    ConfigVetorizacao,
    ModoVetorizacao,
    construir_pipeline_de_medicao,
    todas_as_vetorizacoes,
)

# Semente fixa. Sem ela, as dobras da validação cruzada mudariam a cada
# execução e duas configurações não seriam comparáveis: parte da diferença
# entre elas seria sorteio diferente, não pré-processamento diferente.
SEMENTE = 42

# O primeiro valor de cada enum é a referência das comparações pareadas.
CAMPOS_CATEGORICOS: tuple[tuple[str, type[StrEnum]], ...] = (
    ("stopwords", ModoStopwords),
    ("morfologia", ModoMorfologia),
    ("tokenizacao", Tokenizacao),
)

CAMPOS_DA_CONFIGURACAO: tuple[str, ...] = (
    "minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros",
    "stopwords", "morfologia", "tokenizacao",
)

LARGURA = 118

# As tarefas são independentes e a semente é fixa: as notas saem idênticas em
# série e em paralelo.
PROCESSOS_PARALELOS = -1

# AS RÉGUAS DISPONÍVEIS.
#
# Cada família varre o espaço com ELA PRÓPRIA como instrumento de medida, e não
# herdando o ranking de outra. Sem isso, comparar famílias mede também a
# diferença de texto, e favorece quem produziu o ranking.
#
# O custo não é simétrico, e precisa ser dito antes de alguém disparar a
# varredura: uma validação cruzada de 5 dobras sobre este corpus custa 0,05 s no
# `MultinomialNB`, 0,11 s no `SGDClassifier`, 0,77 s no `LinearSVC` calibrado e
# 18,06 s na regressão logística. A varredura exaustiva são 11.884 execuções —
# minutos para o Naive Bayes, horas para a regressão logística.
#
# Fábricas, e não instâncias: `joblib` serializa o estimador para cada worker, e
# uma instância compartilhada no escopo do módulo viraria estado global entre
# processos.
REGUAS: dict[str, Callable[[], object]] = {
    "multinomialnb": lambda: MultinomialNB(alpha=1.0),
    "logisticregression": lambda: LogisticRegression(max_iter=2000, random_state=SEMENTE),
    "linearsvc": lambda: CalibratedClassifierCV(
        LinearSVC(random_state=SEMENTE), method="sigmoid", cv=3
    ),
    "sgd": lambda: SGDClassifier(
        loss="modified_huber", max_iter=2000, tol=1e-4, random_state=SEMENTE
    ),
}

REGUA_PADRAO = "multinomialnb"


@dataclass(frozen=True)
class Resultado:
    config: ConfigPreprocessamento
    vetorizacao: ConfigVetorizacao
    f1_medio: float
    f1_desvio: float
    tamanho_vocabulario: float
    ordens_equivalentes: int = 1
    e_a_ordem_padrao: bool = True

    # Agrupa as ordens irmãs: mesma configuração, ordens diferentes.
    @property
    def configuracao_sem_a_ordem(self) -> ConfigPreprocessamento:
        return self.config.copiar_com_outra_ordem(ETAPAS)

    def descrever(self) -> str:
        return f"{self.vetorizacao.descrever()} | {self.config.descrever()}"


def contar_colunas(vetorizador) -> int:
    return len(vetorizador.vocabulary_)


# Devolve (F1 médio, desvio, vocabulário médio).
def medir_configuracao(
    textos: list[str], rotulos: list[str], vetorizacao: ConfigVetorizacao, k: int,
    estimador=None,
) -> tuple[float, float, float]:
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    saida = cross_validate(
        construir_pipeline_de_medicao(vetorizacao, estimador),
        textos,
        rotulos,
        cv=dobras,
        scoring="f1_macro",
        return_estimator=True,
    )
    notas = list(saida["test_score"])
    vocabularios = [contar_colunas(e.named_steps["vetorizador"]) for e in saida["estimator"]]
    desvio = statistics.stdev(notas) if len(notas) > 1 else 0.0
    return statistics.mean(notas), desvio, statistics.mean(vocabularios)


# Todas com a ordem padrão; as permutações entram em
# `permutacoes_de_ordem_a_testar`.
def todas_as_configuracoes_de_preprocessamento() -> list[ConfigPreprocessamento]:
    combinacoes = []
    for minusculas, acentos, pontuacao, numeros in itertools.product([False, True], repeat=4):
        for stopwords, morfologia, tokenizacao in itertools.product(
            ModoStopwords, ModoMorfologia, Tokenizacao
        ):
            combinacoes.append(
                ConfigPreprocessamento(
                    minusculas=minusculas,
                    remover_acentos=acentos,
                    remover_pontuacao=pontuacao,
                    remover_numeros=numeros,
                    stopwords=stopwords,
                    morfologia=morfologia,
                    tokenizacao=tokenizacao,
                )
            )
    return combinacoes


# Só as etapas ativas são permutadas; as desligadas vão ao fim apenas para
# satisfazer a validação do dataclass.
#
# A primeira permutação devolvida é `ativas` na própria ordem, que coincide com a
# ordem padrão calculada em `varrer_espaco_de_busca`. `e_a_ordem_padrao` depende
# disso, porque o representante de cada corpus é o primeiro inserido.
def permutacoes_de_ordem_a_testar(base: ConfigPreprocessamento) -> list[tuple[str, ...]]:
    ativas = base.etapas_ativas_na_ordem()
    inativas = tuple(etapa for etapa in ETAPAS if etapa not in ativas)
    return [permutacao + inativas for permutacao in itertools.permutations(ativas)]


# Ordens que geram o mesmo texto são o mesmo experimento e não são treinadas
# duas vezes.
def impressao_digital_do_corpus(corpus: tuple[str, ...]) -> str:
    return hashlib.blake2b("\n".join(corpus).encode("utf-8"), digest_size=16).hexdigest()


# Devolve (resultados, permutações examinadas), em duas fases:
#
#   1. serial: pré-processa e deduplica por hash do corpus. Sequencial porque os
#      caches de lematização e stemming são compartilhados entre configurações.
#   2. paralela: avalia cada par (corpus distinto, vetorização).
#
# Os itens são acumulados numa lista antes do despacho para dar ao agendador
# tarefas grandes e de tamanho parecido.
def varrer_espaco_de_busca(
    textos: list[str],
    rotulos: list[str],
    k: int,
    vetorizacoes: list[ConfigVetorizacao],
    estimador=None,
) -> tuple[list[Resultado], int]:
    permutacoes_examinadas = 0
    configuracoes = todas_as_configuracoes_de_preprocessamento()

    # (config representante, corpus, ordens equivalentes, contém a ordem padrão)
    trabalho: list[tuple] = []

    for numero, base in enumerate(configuracoes, start=1):
        ativas = base.etapas_ativas_na_ordem()
        ordem_padrao = tuple(e for e in ETAPAS if e in ativas) + tuple(
            e for e in ETAPAS if e not in ativas
        )

        corpora_distintos: dict[str, list] = {}
        for ordem in permutacoes_de_ordem_a_testar(base):
            permutacoes_examinadas += 1
            config = base.copiar_com_outra_ordem(ordem)
            corpus = tuple(preprocessar(texto, config) for texto in textos)
            chave = impressao_digital_do_corpus(corpus)

            if chave in corpora_distintos:
                corpora_distintos[chave][2] += 1
                corpora_distintos[chave][3] = corpora_distintos[chave][3] or (ordem == ordem_padrao)
            else:
                corpora_distintos[chave] = [config, list(corpus), 1, ordem == ordem_padrao]

        trabalho.extend(corpora_distintos.values())

        if sys.stdout.isatty():
            print(f"\r  fase 1/2 — {numero}/{len(configuracoes)} configurações pré-processadas",
                  end="", flush=True)

    itens = [
        (config, corpus, equivalentes, tem_a_padrao, vetorizacao)
        for config, corpus, equivalentes, tem_a_padrao in trabalho
        for vetorizacao in vetorizacoes
    ]

    if sys.stdout.isatty():
        print(f"\r  fase 2/2 — {len(itens)} avaliações em paralelo{' ' * 30}", end="", flush=True)

    medidas = Parallel(n_jobs=PROCESSOS_PARALELOS)(
        delayed(medir_configuracao)(corpus, rotulos, vetorizacao, k, estimador)
        for _, corpus, _, _, vetorizacao in itens
    )

    resultados = [
        Resultado(config, vetorizacao, media, desvio, vocabulario, equivalentes, tem_a_padrao)
        for (config, _, equivalentes, tem_a_padrao, vetorizacao), (media, desvio, vocabulario)
        in zip(itens, medidas, strict=True)
    ]

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados, permutacoes_examinadas


def medir_efeito_das_etapas_booleanas(
    resultados: list[Resultado],
) -> list[tuple[str, float, float, float]]:
    linhas: list[tuple[str, float, float, float]] = []
    for etapa in ("minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros"):
        com = [r.f1_medio for r in resultados if getattr(r.config, etapa)]
        sem = [r.f1_medio for r in resultados if not getattr(r.config, etapa)]
        media_com, media_sem = statistics.mean(com), statistics.mean(sem)
        linhas.append((etapa, media_com, media_sem, media_com - media_sem))

    return sorted(linhas, key=lambda linha: linha[3], reverse=True)


# Média simples seria enviesada: `manter` e `nenhuma` deixam a configuração com
# uma etapa a menos e, portanto, com menos permutações de ordem. O pareamento
# mantém tudo o mais constante, restringindo os grupos à ordem padrão.
def comparar_valores_pareados(
    resultados: list[Resultado], campo: str, enum_do_campo: type[StrEnum]
) -> tuple[list[tuple[str, float, float]], int]:
    outros_campos = tuple(c for c in CAMPOS_DA_CONFIGURACAO if c != campo)
    grupos: dict[tuple, dict[StrEnum, float]] = defaultdict(dict)

    for resultado in resultados:
        if not resultado.e_a_ordem_padrao:
            continue
        chave = tuple(getattr(resultado.config, c) for c in outros_campos) + (resultado.vetorizacao,)
        grupos[chave][getattr(resultado.config, campo)] = resultado.f1_medio

    valores = list(enum_do_campo)
    completos = [g for g in grupos.values() if len(g) == len(valores)]
    if not completos:
        return [], 0

    referencia = statistics.mean(g[valores[0]] for g in completos)
    linhas = []
    for valor in valores:
        media = statistics.mean(g[valor] for g in completos)
        linhas.append((valor.value, media, media - referencia))
    return linhas, len(completos)


# Só entram os grupos completos, senão a comparação mediria a amostra e não a
# escolha. O tamanho esperado é derivado de `todas_as_vetorizacoes()`: escrito à
# mão, ele deixa de casar com qualquer grupo quando uma vetorização é
# acrescentada, e a tabela some do relatório sem erro.
def medir_efeito_da_vetorizacao(
    resultados: list[Resultado],
) -> list[tuple[str, float, float, int]]:
    por_configuracao: dict[ConfigPreprocessamento, dict[ConfigVetorizacao, float]] = defaultdict(dict)
    for resultado in resultados:
        por_configuracao[resultado.config][resultado.vetorizacao] = resultado.f1_medio

    esperadas = len(todas_as_vetorizacoes())
    completos = [g for g in por_configuracao.values() if len(g) == esperadas]
    if not completos:
        return []

    comparacoes = (
        # nome, quem entra no "com", quem é elegível para a comparação
        ("tfidf (vs bow)", lambda v: v.modo is ModoVetorizacao.TFIDF, lambda v: True),
        ("bigrama (vs só uni)", lambda v: v.n_max >= 2, lambda v: True),
    )

    linhas: list[tuple[str, float, float, int]] = []
    for nome, no_grupo, elegivel in comparacoes:
        com, sem = [], []
        for grupo in completos:
            candidatas = {v: f for v, f in grupo.items() if elegivel(v)}
            dentro = [f for v, f in candidatas.items() if no_grupo(v)]
            fora = [f for v, f in candidatas.items() if not no_grupo(v)]
            if dentro and fora:
                com.append(statistics.mean(dentro))
                sem.append(statistics.mean(fora))
        if com:
            linhas.append((nome, statistics.mean(com), statistics.mean(sem), len(com)))

    return sorted(linhas, key=lambda linha: linha[1] - linha[2], reverse=True)


@dataclass
class AnaliseDeOrdem:
    grupos_sensiveis: int
    grupos_totais: int
    amplitude_media: float
    amplitude_maxima: float
    par_extremo: tuple[Resultado, Resultado] | None
    ordem_padrao_venceu: int
    ordem_padrao_avaliada: int
    perda_media_da_ordem_padrao: float


# Cada grupo reúne resultados idênticos em tudo menos na ordem das etapas, de
# modo que a amplitude de F1 dentro dele é o efeito da ordem.
def analisar_efeito_da_ordem(resultados: list[Resultado]) -> AnaliseDeOrdem:
    grupos: dict[tuple, list[Resultado]] = defaultdict(list)
    for resultado in resultados:
        grupos[(resultado.configuracao_sem_a_ordem, resultado.vetorizacao)].append(resultado)

    amplitudes: list[float] = []
    par_extremo = None
    amplitude_maxima = 0.0
    padrao_venceu = padrao_avaliada = 0
    perdas: list[float] = []

    for membros in grupos.values():
        if len(membros) < 2:
            continue

        melhor = max(membros, key=lambda r: r.f1_medio)
        pior = min(membros, key=lambda r: r.f1_medio)
        amplitude = melhor.f1_medio - pior.f1_medio
        amplitudes.append(amplitude)

        if amplitude > amplitude_maxima:
            amplitude_maxima, par_extremo = amplitude, (melhor, pior)

        padrao = next((r for r in membros if r.e_a_ordem_padrao), None)
        if padrao is not None:
            padrao_avaliada += 1
            perdas.append(melhor.f1_medio - padrao.f1_medio)
            if padrao.f1_medio >= melhor.f1_medio - 1e-12:
                padrao_venceu += 1

    return AnaliseDeOrdem(
        grupos_sensiveis=len(amplitudes),
        grupos_totais=len(grupos),
        amplitude_media=statistics.mean(amplitudes) if amplitudes else 0.0,
        amplitude_maxima=amplitude_maxima,
        par_extremo=par_extremo,
        ordem_padrao_venceu=padrao_venceu,
        ordem_padrao_avaliada=padrao_avaliada,
        perda_media_da_ordem_padrao=statistics.mean(perdas) if perdas else 0.0,
    )


def imprimir_ranking(resultados: list[Resultado], top: int) -> None:
    print(f"{'#':>3}  {'F1-macro':>8}  {'±dp':>6}  {'vocab':>6}  combinação")
    print("-" * LARGURA)
    for posicao, resultado in enumerate(resultados[:top], start=1):
        print(
            f"{posicao:>3}  {resultado.f1_medio:>8.4f}  {resultado.f1_desvio:>6.4f}  "
            f"{resultado.tamanho_vocabulario:>6.0f}  {resultado.descrever()}"
        )
    pior = resultados[-1]
    print("-" * LARGURA)
    print(
        f"pior  {pior.f1_medio:>7.4f}  {pior.f1_desvio:>6.4f}  "
        f"{pior.tamanho_vocabulario:>6.0f}  {pior.descrever()}"
    )


TITULOS_DOS_CAMPOS = {
    "stopwords": "TRATAMENTO DE STOPWORDS",
    "morfologia": "NORMALIZAÇÃO MORFOLÓGICA — stemming contra lematização",
    "tokenizacao": "ESTRATÉGIA DE TOKENIZAÇÃO",
}


def imprimir_varredura(resultados: list[Resultado], top: int, permutacoes: int) -> None:
    titulo = "VARREDURA EXAUSTIVA — pré-processamento x vetorização"
    print(f"\n{'=' * LARGURA}")
    print(f"{titulo:^{LARGURA}}")
    print("=" * LARGURA)
    imprimir_ranking(resultados, top)

    print(f"\n{'EFEITO DE CADA ETAPA BOOLEANA':^{LARGURA}}")
    print(f"{'etapa':>24}  {'com':>8}  {'sem':>10}  {'efeito':>9}")
    print("-" * LARGURA)
    for nome, com, sem, efeito in medir_efeito_das_etapas_booleanas(resultados):
        marca = "  <- atrapalha" if efeito < -0.01 else ("  <- ajuda" if efeito > 0.01 else "")
        print(f"{nome:>24}  {com:>8.4f}  {sem:>10.4f}  {efeito:>+9.4f}{marca}")

    for campo, enum_do_campo in CAMPOS_CATEGORICOS:
        linhas, pareamentos = comparar_valores_pareados(resultados, campo, enum_do_campo)
        cabecalho = f"{TITULOS_DOS_CAMPOS[campo]} — pareado em {pareamentos} configurações"
        referencia = list(enum_do_campo)[0].value
        print(f"\n{cabecalho:^{LARGURA}}")
        print(f"{'opção':>24}  {'F1 médio':>8}  {'vs ' + referencia:>22}")
        print("-" * LARGURA)
        for valor, media, diferenca in linhas:
            print(f"{valor:>24}  {media:>8.4f}  {diferenca:>+22.4f}")

        if campo == "stopwords" and len(linhas) == 3:
            ganho = linhas[2][1] - linhas[1][1]
            print(f"{'':>24}  preservar as negações recupera {ganho:+.4f} em relação a remover tudo")
        if campo == "morfologia" and len(linhas) == 3:
            diferenca = linhas[2][1] - linhas[1][1]
            vencedor = "lematização" if diferenca > 0 else "stemming"
            print(f"{'':>24}  {vencedor} leva por {abs(diferenca):.4f}")

    # Cada corpus foi avaliado sob TODAS as vetorizações, e é isso que torna o
    # efeito delas mensurável: a comparação é pareada.
    linhas_vetorizacao = medir_efeito_da_vetorizacao(resultados)
    if linhas_vetorizacao:
        cabecalho = f"EFEITO DA VETORIZAÇÃO — pareado em {linhas_vetorizacao[0][3]} pré-processamentos"
        print(f"\n{cabecalho:^{LARGURA}}")
        print(f"{'escolha':>24}  {'com':>8}  {'sem':>10}  {'efeito':>9}")
        print("-" * LARGURA)
        for nome, com, sem, _ in linhas_vetorizacao:
            efeito = com - sem
            marca = "  <- atrapalha" if efeito < -0.01 else ("  <- ajuda" if efeito > 0.01 else "")
            print(f"{nome:>24}  {com:>8.4f}  {sem:>10.4f}  {efeito:>+9.4f}{marca}")

    analise = analisar_efeito_da_ordem(resultados)
    print(f"\n{'A ORDEM IMPORTA?':^{LARGURA}}")
    print("-" * LARGURA)
    print(f"  Permutações examinadas                        : {permutacoes}")
    print(f"  Execuções distintas depois da deduplicação    : {len(resultados)}")
    print(f"  Grupos em que a ordem muda o texto            : {analise.grupos_sensiveis} de {analise.grupos_totais}")
    print(f"  Amplitude média de F1 dentro desses grupos    : {analise.amplitude_media:.4f}")
    print(f"  Amplitude máxima                              : {analise.amplitude_maxima:.4f}")
    if analise.par_extremo:
        melhor, pior = analise.par_extremo
        print(f"    melhor: {melhor.f1_medio:.4f}  {melhor.descrever()}")
        print(f"    pior  : {pior.f1_medio:.4f}  {pior.descrever()}")
    if analise.ordem_padrao_avaliada:
        porcentagem = 100 * analise.ordem_padrao_venceu / analise.ordem_padrao_avaliada
        print(f"  Ordem padrão foi a melhor do grupo            : "
              f"{analise.ordem_padrao_venceu}/{analise.ordem_padrao_avaliada} ({porcentagem:.0f}%)")
        print(f"  Perda média por usar a ordem padrão           : {analise.perda_media_da_ordem_padrao:.4f}")


def empatadas_com_a_melhor(resultados: list[Resultado]) -> list[Resultado]:
    melhor = resultados[0]
    return [r for r in resultados if r.f1_medio >= melhor.f1_medio - melhor.f1_desvio]


def escolher_recomendada(empatadas: list[Resultado]) -> Resultado:
    return min(
        empatadas,
        key=lambda r: (
            len(r.config.etapas_ativas_na_ordem()),
            r.vetorizacao.n_max,
            not r.e_a_ordem_padrao,
            -r.f1_medio,
        ),
    )


def imprimir_recomendacao(resultados: list[Resultado]) -> None:
    melhor = resultados[0]
    empatadas = empatadas_com_a_melhor(resultados)
    mais_simples = escolher_recomendada(empatadas)

    print(f"\n{'=' * LARGURA}")
    print(f"{'RECOMENDAÇÃO':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"Melhor absoluta : {melhor.f1_medio:.4f}  {melhor.descrever()}")
    print(f"Dentro de 1 desvio padrão da melhor: {len(empatadas)} de {len(resultados)} — empatadas na prática.")
    print(f"Mais simples entre as empatadas: {mais_simples.f1_medio:.4f}  {mais_simples.descrever()}")
    print("\n^ é esta que vale a pena adotar: dentro do erro da melhor, com menos etapas")
    print("  para manter e na ordem padrão, que não depende do sorteio das dobras.")


# O SUFIXO NÃO É COSMÉTICO.
#
# Sem ele, varrer com a segunda régua sobrescreveria o ranking da primeira, e o
# comparativo passaria a ler para todas as famílias o ranking da última que
# rodou — a assimetria voltaria em silêncio, com todos os arquivos no lugar.
#
# A régua padrão mantém o nome histórico, sem sufixo: relatórios e testes que já
# apontam para `comparativo_preprocessamento.csv` continuam valendo.
def nome_do_relatorio(regua: str, extensao: str) -> str:
    base = "comparativo_preprocessamento"
    sufixo = "" if regua == REGUA_PADRAO else f"_{regua}"
    return f"{base}{sufixo}.{extensao}"


def escrever_relatorio(
    resultados: list[Resultado],
    dataset: Path,
    k: int,
    permutacoes: int,
    regua: str = REGUA_PADRAO,
) -> None:
    dir_resultados = garantir_dir_de_resultados()

    caminho_csv = dir_resultados / nome_do_relatorio(regua, "csv")
    with caminho_csv.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(
            ["posicao", "f1_macro_medio", "desvio_padrao", "vocabulario_medio", "vetorizador",
             "n_max", "ordem", "ordens_equivalentes", "e_a_ordem_padrao", "minusculas", "remover_acentos",
             "remover_pontuacao", "remover_numeros", "stopwords", "morfologia", "tokenizacao"]
        )
        for posicao, r in enumerate(resultados, start=1):
            c = r.config
            escritor.writerow(
                [posicao, f"{r.f1_medio:.6f}", f"{r.f1_desvio:.6f}",
                 f"{r.tamanho_vocabulario:.1f}", r.vetorizacao.modo.value, r.vetorizacao.n_max,
                 ">".join(c.etapas_ativas_na_ordem()), r.ordens_equivalentes, r.e_a_ordem_padrao,
                 c.minusculas, c.remover_acentos, c.remover_pontuacao, c.remover_numeros,
                 c.stopwords.value, c.morfologia.value, c.tokenizacao.value]
            )

    linhas = [
        "# Comparativo de pré-processamento e vetorização",
        "",
        f"- Dataset: `{dataset.name}`",
        f"- Validação cruzada estratificada de {k} dobras, semente {SEMENTE}",
        "- Régua fixa: `MultinomialNB(alpha=1.0)`, instrumento de medida, não o modelo final",
        "- A MESMA régua nas quatro vetorizações, que são todas esparsas: é o que torna a "
        "comparação entre elas identificável",
        "",
        "## Varredura exaustiva — pré-processamento x vetorização",
        "",
        "Produto cartesiano completo: cada pré-processamento contra as "
        f"{len(todas_as_vetorizacoes())} vetorizações.",
        f"Permutações de ordem examinadas: {permutacoes}. Execuções distintas: {len(resultados)}.",
        "",
        "### Efeito de cada etapa booleana",
        "",
        "| etapa | com | sem | efeito |",
        "|---|---|---|---|",
    ]
    for nome, com, sem, efeito in medir_efeito_das_etapas_booleanas(resultados):
        linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {efeito:+.4f} |")

    for campo, enum_do_campo in CAMPOS_CATEGORICOS:
        linhas_campo, pareamentos = comparar_valores_pareados(resultados, campo, enum_do_campo)
        referencia = list(enum_do_campo)[0].value
        linhas += [
            "", f"### {campo.capitalize()}", "",
            f"Comparação **pareada** em {pareamentos} configurações idênticas nas demais escolhas.",
            "", f"| opção | F1 médio | vs {referencia} |", "|---|---|---|",
        ]
        for valor, media, diferenca in linhas_campo:
            linhas.append(f"| {valor} | {media:.4f} | {diferenca:+.4f} |")

    analise = analisar_efeito_da_ordem(resultados)
    linhas += [
        "", "### A ordem importa?", "",
        f"- Grupos em que a ordem muda o texto: **{analise.grupos_sensiveis} de {analise.grupos_totais}**",
        f"- Amplitude média de F1 nesses grupos: **{analise.amplitude_media:.4f}**",
        f"- Amplitude máxima: **{analise.amplitude_maxima:.4f}**",
    ]
    if analise.ordem_padrao_avaliada:
        porcentagem = 100 * analise.ordem_padrao_venceu / analise.ordem_padrao_avaliada
        linhas.append(
            f"- Ordem padrão foi a melhor em **{analise.ordem_padrao_venceu}/"
            f"{analise.ordem_padrao_avaliada} ({porcentagem:.0f}%)** dos grupos"
        )

    linhas_vetorizacao = medir_efeito_da_vetorizacao(resultados)
    if linhas_vetorizacao:
        linhas += [
            "", "### Efeito da vetorização", "",
            f"Comparação **pareada** em {linhas_vetorizacao[0][3]} pré-processamentos: cada um foi",
            f"avaliado sob as {len(todas_as_vetorizacoes())} vetorizações, e é esse conjunto que se compara entre si.",
            "", "| escolha | com | sem | efeito |", "|---|---|---|---|",
        ]
        for nome, com, sem, _ in linhas_vetorizacao:
            linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {com - sem:+.4f} |")

    linhas += ["", "### Ranking (top 30)", "",
               "| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |", "|---|---|---|---|---|---|"]
    for posicao, r in enumerate(resultados[:30], start=1):
        linhas.append(
            f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | {r.tamanho_vocabulario:.0f} "
            f"| {r.vetorizacao.descrever()} | {r.config.descrever()} |"
        )
    caminho_md = dir_resultados / nome_do_relatorio(regua, "md")
    caminho_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em:\n  {caminho_csv}\n  {caminho_md}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca a melhor configuração de pré-processamento e vetorização.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="número de dobras da validação cruzada")
    parser.add_argument("--top", type=int, default=10, help="quantas linhas mostrar em cada ranking")
    parser.add_argument(
        "--regua", choices=sorted(REGUAS), default=REGUA_PADRAO,
        help="qual classificador serve de instrumento de medida. Cada família precisa "
             "varrer o espaço com ela própria, senão herda a escolha de texto de outra.",
    )
    args = parser.parse_args(argv)
    estimador = REGUAS[args.regua]()

    with args.dataset.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    textos = [linha["texto"] for linha in linhas]
    rotulos = [linha["intencao"] for linha in linhas]

    vetorizacoes = todas_as_vetorizacoes()

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Distribuição: {dict(Counter(rotulos))}")
    print(f"Configurações de pré-processamento: {len(todas_as_configuracoes_de_preprocessamento())}")
    print("Varredura de ordem: todas as permutações das etapas ativas")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}")
    print(f"Régua: {args.regua} ({type(estimador).__name__})")
    print(f"Varredura EXAUSTIVA: cada pré-processamento contra as {len(vetorizacoes)} vetorizações\n")

    resultados, permutacoes = varrer_espaco_de_busca(
        textos, rotulos, args.k, vetorizacoes, estimador
    )
    imprimir_varredura(resultados, args.top, permutacoes)
    imprimir_recomendacao(resultados)
    escrever_relatorio(resultados, args.dataset, args.k, permutacoes, args.regua)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
