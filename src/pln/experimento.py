# =============================================================================
# experimento.py — Busca pela melhor configuração do pipeline
# =============================================================================
# O que este script responde, com número em vez de opinião:
#
# 1. Quais etapas de pré-processamento ajudam neste dataset?
# 2. A ORDEM das etapas importa? A ordem padrão é a melhor?
# 3. Remover stopwords ajuda? E remover preservando as negações?
# 4. Stemming ou lematização — qual reduz melhor as palavras?
# 5. Qual estratégia de tokenização produz o melhor vocabulário?
# 6. Qual vetorização e qual janela de n-grama?
#
# MÉTODO: VARREDURA EXAUSTIVA, E SÓ
# ---------------------------------
# O experimento testa o produto cartesiano completo — cada pré-processamento
# contra cada vetorização. É o único método que encontra o ótimo global, e no
# nosso tamanho de dataset custa alguns minutos.
#
# Existiu aqui uma alternativa `--duas-fases`, que varria o pré-processamento
# com a vetorização fixa e só depois varria a vetorização sobre as melhores.
# Custava 1/4 das avaliações e foi REMOVIDA, porque busca em estágios não
# garante o ótimo global e neste dataset comprovadamente não o encontrava: o
# melhor pré-processamento sob TF-IDF não era o melhor sob bag-of-words, e a
# combinação vencedora se perdia por 0,0078 de F1.
#
# Manter os dois caminhos custava um parâmetro `duas_fases` atravessando seis
# funções e dois formatos de relatório, para oferecer um resultado que o próprio
# comentário desaconselhava usar. Se um dia a varredura completa ficar cara
# demais, o caminho é reduzir o espaço de busca de propósito — não voltar a um
# método que erra de um jeito difícil de perceber.
#
# O ESPAÇO DE BUSCA DO PRÉ-PROCESSAMENTO
# ---------------------------------------
#     4 etapas booleanas (minúsculas, acentos, pontuação, números) -> 2^4 = 16
#     3 modos de stopwords (manter / remover tudo / preservar não) ->       3
#     3 modos de morfologia (nenhuma / stemming / lematização)     ->       3
#     3 tokenizações (split / regex / linguística)                 ->       3
#                                                                     ---------
#     configurações                                                ->     432
#
#     para cada uma, TODAS as permutações das etapas ativas        ->  19.767
#
# Ordens que produzem TEXTO IDÊNTICO são o mesmo experimento e são
# deduplicadas — na prática, ~95% do trabalho some.
#
# USO
# ---
#     python -m pln.experimento                    # varredura exaustiva (padrão)
#     python -m pln.experimento --dataset seus_dados.csv --k 10
#     python -m pln.experimento --sem-ordem        # só a ordem padrão
# =============================================================================

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

# Campos categóricos da configuração. Cada um vira uma comparação pareada.
# O primeiro valor de cada enum é a referência ("não fazer nada").
CAMPOS_CATEGORICOS: tuple[tuple[str, type[StrEnum]], ...] = (
    ("stopwords", ModoStopwords),
    ("morfologia", ModoMorfologia),
    ("tokenizacao", Tokenizacao),
)

# Campos que identificam uma configuração, usados para parear comparações.
CAMPOS_DA_CONFIGURACAO: tuple[str, ...] = (
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
    e_a_ordem_padrao: bool = True

    # Usada para agrupar as ordens irmãs: mesma configuração, ordens diferentes.
    @property
    def configuracao_sem_a_ordem(self) -> ConfigPreprocessamento:
        return self.config.copiar_com_outra_ordem(ETAPAS)

    def descrever(self) -> str:
        return f"{self.vetorizacao.descrever()} | {self.config.descrever()}"


# Quantas colunas a matriz tem — o "tamanho do vocabulário" do ranking.
#
# As duas famílias de vetorização respondem isso de formas diferentes, e nenhuma
# delas é errada: uma esparsa tem `vocabulary_`, um termo por coluna, e o número
# cresce com o corpus; uma densa tem largura FIXA, e o número não depende do
# corpus nenhum. Ler `vocabulary_` direto quebrava com AttributeError assim que a
# vetorização densa entrou no espaço de busca.
def contar_colunas(vetorizador) -> int:
    vocabulario = getattr(vetorizador, "vocabulary_", None)
    if vocabulario is not None:
        return len(vocabulario)
    return len(vetorizador.get_feature_names_out())


# Validação cruzada estratificada. Devolve (F1 médio, desvio, vocabulário médio).
#
# Validação cruzada e não uma divisão única porque, com poucas centenas de
# exemplos, uma divisão só daria uma nota dependente demais de quais frases
# caíram no teste — trocando a semente, a "melhor" configuração mudaria.
#
# ESTRATIFICADA para que cada dobra tenha as três intenções na mesma proporção;
# sem isso uma dobra poderia sair sem nenhum "alerta" e o F1 daquela classe
# ficaria indefinido.
#
# F1-macro e não acurácia porque acurácia engana com classes desbalanceadas: se
# 80% fossem consulta, responder "consulta" para tudo daria 80% e seria inútil.
# O macro tira média por classe, então a rara pesa igual à comum.
def medir_configuracao(
    textos: list[str], rotulos: list[str], vetorizacao: ConfigVetorizacao, k: int
) -> tuple[float, float, float]:
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    saida = cross_validate(
        construir_pipeline_de_medicao(vetorizacao),
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


# -----------------------------------------------------------------------------
# Varredura do pré-processamento
# -----------------------------------------------------------------------------


# As 432 configurações, todas com a ordem padrão. As permutações de ordem
# entram depois, por configuração, em `permutacoes_de_ordem_a_testar`.
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


# Só as etapas ATIVAS são permutadas — permutar uma etapa desligada não muda
# nada e multiplicaria o custo à toa. As desligadas são acrescentadas ao fim,
# na ordem padrão, apenas para satisfazer a validação do dataclass.
def permutacoes_de_ordem_a_testar(
    base: ConfigPreprocessamento, variar_ordem: bool
) -> list[tuple[str, ...]]:
    ativas = base.etapas_ativas_na_ordem()
    if not variar_ordem:
        return [base.ordem]

    inativas = tuple(etapa for etapa in ETAPAS if etapa not in ativas)
    return [permutacao + inativas for permutacao in itertools.permutations(ativas)]


# Identidade do corpus produzido. Duas ordens que geram o mesmo texto são o
# mesmo experimento e não precisam ser treinadas duas vezes.
def impressao_digital_do_corpus(corpus: tuple[str, ...]) -> str:
    return hashlib.blake2b("\n".join(corpus).encode("utf-8"), digest_size=16).hexdigest()


# Varre o pré-processamento e devolve (resultados, permutações examinadas).
#
# Por padrão `vetorizacoes` traz todas, e o resultado é o produto
# cartesiano completo. Com `--duas-fases` traz só a régua, e esta função passa
# a ser a Fase 1.
def varrer_espaco_de_busca(
    textos: list[str],
    rotulos: list[str],
    k: int,
    variar_ordem: bool,
    vetorizacoes: list[ConfigVetorizacao],
) -> tuple[list[Resultado], int]:
    resultados: list[Resultado] = []
    permutacoes_examinadas = 0
    configuracoes = todas_as_configuracoes_de_preprocessamento()

    for numero, base in enumerate(configuracoes, start=1):
        ativas = base.etapas_ativas_na_ordem()
        ordem_padrao = tuple(e for e in ETAPAS if e in ativas) + tuple(
            e for e in ETAPAS if e not in ativas
        )

        # impressão digital -> [config representante, corpus, ordens equivalentes, contém a ordem padrão]
        corpora_distintos: dict[str, list] = {}
        for ordem in permutacoes_de_ordem_a_testar(base, variar_ordem):
            permutacoes_examinadas += 1
            config = base.copiar_com_outra_ordem(ordem)
            corpus = tuple(preprocessar(texto, config) for texto in textos)
            chave = impressao_digital_do_corpus(corpus)

            if chave in corpora_distintos:
                corpora_distintos[chave][2] += 1
                corpora_distintos[chave][3] = corpora_distintos[chave][3] or (ordem == ordem_padrao)
            else:
                corpora_distintos[chave] = [config, list(corpus), 1, ordem == ordem_padrao]

        for config, corpus, equivalentes, tem_a_padrao in corpora_distintos.values():
            for vetorizacao in vetorizacoes:
                media, desvio, vocabulario = medir_configuracao(
                    corpus, rotulos, vetorizacao, k
                )
                resultados.append(
                    Resultado(config, vetorizacao, media, desvio, vocabulario, equivalentes, tem_a_padrao)
                )

        if sys.stdout.isatty():
            print(f"\r  {numero}/{len(configuracoes)} configurações de pré-processamento", end="", flush=True)

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados, permutacoes_examinadas


# -----------------------------------------------------------------------------
# Análises
# -----------------------------------------------------------------------------


# Efeito médio de cada etapa booleana, sobre TODAS as execuções.
#
# Esta é a leitura confiável, e não o topo do ranking. Com poucos dados, a
# combinação em primeiro lugar chegou lá em boa parte por sorteio — o desvio
# padrão costuma ser maior que a diferença entre as dez primeiras.
#
# Aqui cada média resume metade do espaço de busca, então o ruído das outras
# escolhas se cancela e o que sobra é o efeito daquela etapa isolada.
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


# Compara os valores de um campo categórico, PAREADO. Vale para os três campos
# de múltipla escolha: stopwords, morfologia e tokenização.
#
# POR QUE PAREADO, E NÃO A MÉDIA SIMPLES
# ---------------------------------------
# Média simples por valor seria enviesada. Quando stopwords é `manter`, ou
# morfologia é `nenhuma`, a etapa correspondente não entra na lista de ativas —
# a configuração fica com UMA ETAPA A MENOS e, portanto, com menos permutações
# de ordem. Comparar essa média com a dos demais valores misturaria dois
# efeitos: o do tratamento em si e o de ter menos etapas.
#
# O pareamento resolve: para cada conjunto idêntico das demais escolhas
# (mesmas etapas, mesmos outros campos categóricos, mesma vetorização, todos na
# ordem padrão), pegam-se todos os valores do campo e comparam-se entre si.
# Tudo o mais constante — a diferença só pode vir do campo em questão.
#
# A referência é o PRIMEIRO valor do enum, que é sempre o "não fazer nada".
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


# O efeito de cada escolha de vetorização, comparada de forma PAREADA.
#
# Cada pré-processamento foi avaliado sob TODAS as vetorizações. Só entram os
# grupos completos: comparar um pré-processamento que rodou sob cinco
# vetorizações com outro que rodou sob duas mediria a amostra, não a escolha.
#
# CADA COMPARAÇÃO TEM O SEU PRÓPRIO UNIVERSO, e isso não é detalhe. Perguntar
# "bigrama ajuda?" só faz sentido entre as vetorizações que TÊM janela de
# n-grama — a densa não tem, e incluí-la no lado "sem bigrama" jogaria a média
# de um pipeline completamente diferente dentro da comparação, fazendo o bigrama
# parecer melhor ou pior por um motivo que não é o bigrama.
#
# O `len(g) == 4` que existia aqui era o número de vetorizações da época, escrito
# à mão. Quando a quinta entrou, nenhum grupo tinha mais tamanho 4, a lista saía
# vazia e a tabela inteira DESAPARECIA do relatório — sem erro, sem aviso. Agora
# o tamanho esperado é derivado de `todas_as_vetorizacoes()`.
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

    e_densa = ConfigVetorizacao.produz_vetores_densos
    comparacoes = (
        # nome, quem entra no "com", quem é elegível para a comparação
        ("tfidf (vs bow)",
         lambda v: v.modo is ModoVetorizacao.TFIDF,
         lambda v: not e_densa(v)),
        ("bigrama (vs só uni)",
         lambda v: v.n_max >= 2,
         lambda v: not e_densa(v)),
        ("embedding (vs esparsas)",
         e_densa,
         lambda v: True),
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


# Responde: a ordem importa, e a ordem padrão é a melhor?
#
# Um GRUPO é o conjunto de resultados que compartilham exatamente as mesmas
# etapas e a mesma vetorização, diferindo APENAS na ordem. Dentro de um grupo,
# tudo o mais é constante — então qualquer diferença de F1 só pode ter vindo da
# ordem. É um experimento controlado, e é o que dá direito de afirmar causa em
# vez de correlação.
#
# A amplitude do grupo (maior F1 menos menor F1) é o tamanho do efeito da ordem
# naquela configuração.
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


# -----------------------------------------------------------------------------
# Saída no terminal
# -----------------------------------------------------------------------------


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


def imprimir_varredura(
    resultados: list[Resultado], top: int, permutacoes: int, variar_ordem: bool
) -> None:
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

    if variar_ordem:
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


def imprimir_recomendacao(resultados: list[Resultado]) -> None:
    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatadas = [r for r in resultados if r.f1_medio >= limiar]
    mais_simples = min(
        empatadas,
        key=lambda r: (len(r.config.etapas_ativas_na_ordem()), r.vetorizacao.n_max, -r.f1_medio),
    )

    print(f"\n{'=' * LARGURA}")
    print(f"{'RECOMENDAÇÃO':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"Melhor absoluta : {melhor.f1_medio:.4f}  {melhor.descrever()}")
    print(f"Dentro de 1 desvio padrão da melhor: {len(empatadas)} de {len(resultados)} — empatadas na prática.")
    print(f"Mais simples entre as empatadas: {mais_simples.f1_medio:.4f}  {mais_simples.descrever()}")
    print("\n^ é esta que vale a pena adotar: mesmo resultado, menos etapas para manter.")


# -----------------------------------------------------------------------------
# Relatório em arquivo
# -----------------------------------------------------------------------------


def escrever_relatorio(
    resultados: list[Resultado],
    dataset: Path,
    k: int,
    permutacoes: int,
    variar_ordem: bool,
) -> None:
    dir_resultados = garantir_dir_de_resultados()

    caminho_csv = dir_resultados / "comparativo_preprocessamento.csv"
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
        "- Classificador fixo: `MultinomialNB(alpha=1.0)` — régua de medição, não o modelo final",
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

    if variar_ordem:
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
    caminho_md = dir_resultados / "comparativo_preprocessamento.md"
    caminho_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em:\n  {caminho_csv}\n  {caminho_md}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca a melhor configuração de pré-processamento e vetorização.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="número de dobras da validação cruzada")
    parser.add_argument("--top", type=int, default=10, help="quantas linhas mostrar em cada ranking")
    parser.add_argument("--sem-ordem", action="store_true", help="usa só a ordem padrão (execução rápida)")
    args = parser.parse_args(argv)

    with args.dataset.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    textos = [linha["texto"] for linha in linhas]
    rotulos = [linha["intencao"] for linha in linhas]

    variar_ordem = not args.sem_ordem
    vetorizacoes = todas_as_vetorizacoes()

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Distribuição: {dict(Counter(rotulos))}")
    print(f"Configurações de pré-processamento: {len(todas_as_configuracoes_de_preprocessamento())}")
    print(f"Varredura de ordem: {'todas as permutações das etapas ativas' if variar_ordem else 'somente a ordem padrão'}")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}")
    print(f"Varredura EXAUSTIVA: cada pré-processamento contra as {len(vetorizacoes)} vetorizações\n")

    resultados, permutacoes = varrer_espaco_de_busca(textos, rotulos, args.k, variar_ordem, vetorizacoes)
    imprimir_varredura(resultados, args.top, permutacoes, variar_ordem)
    imprimir_recomendacao(resultados)
    escrever_relatorio(resultados, args.dataset, args.k, permutacoes, variar_ordem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
