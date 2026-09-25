# Compara famílias de classificador sobre o MESMO texto.
#
# POR QUE ISTO EXISTE AGORA
# -------------------------
# A Seção 3.3.2 escolheu `MultinomialNB` por velocidade, e o argumento era
# correto: são 11.644 medições na varredura de pré-processamento, e a regressão
# logística é 430 vezes mais lenta na vetorização mais cara do espaço. Com
# `LogisticRegression`, a varredura passaria de minutos para mais de dez horas.
#
# Só que esse argumento é sobre o INSTRUMENTO DE MEDIDA, não sobre o produto. O
# produto classifica uma frase por vez, em microssegundos, e o custo de treino
# é pago uma vez por dataset. Com F1-macro 17,6 pontos abaixo do RNF03, a
# pergunta "outra família fecha a distância?" nunca foi medida — e é barata.
#
# O QUE MUDA SE OUTRO VENCER
# --------------------------
# A varredura de pré-processamento CONTINUA rodando sobre `MultinomialNB`, que
# é o que a torna praticável. Trocar o produto sem trocar a régua quebra a
# condição de validade registrada na Seção 3.3.2: o pré-processamento teria
# sido escolhido medindo com um modelo que não é o que roda.
#
# Isso não proíbe a troca — mas é um custo real, e a Seção 3.3.2 precisa passar
# a registrá-lo. Um ganho de um ponto de F1 não paga; um ganho que atravesse o
# limite do RNF03, paga.
#
# TODO CANDIDATO PRECISA DE `predict_proba`
# -----------------------------------------
# A regra de rejeição de `pln.intencao` compara confiança contra limiar, e
# cobertura e aceitação indevida são definidas sobre ela. Um classificador sem
# probabilidade não é comparável aqui — daí `LinearSVC` entrar embrulhado em
# `CalibratedClassifierCV`, e o `SGDClassifier` usar `modified_huber`.
#
# BUSCA CONJUNTA: TEXTO x ALGORITMO
# ---------------------------------
# Medir as famílias sobre UMA configuração de texto — a que o `MultinomialNB`
# escolheu — responderia a pergunta errada. O melhor pré-processamento para uma
# fronteira discriminativa não é necessariamente o melhor para contagem por
# classe, e comparar todo mundo no texto de um deles dá vantagem a esse um.
#
# `ajuste_fino.py` diz, hoje, que "o classificador não é eixo de busca". Aqui
# ele é: cada família é medida sobre as N melhores configurações de texto do
# relatório do experimento, e cada uma fica com a SUA melhor.
#
# LIMITE HERDADO, E DECLARADO: é busca em estágios, e o estágio 1 ranqueia com
# `MultinomialNB`. Se o texto ideal de outra família estiver na posição 800 do
# ranking dele, este comparativo não o encontra. É a mesma limitação que
# `ajuste_fino.py` já aceita e documenta; `--top-pre 0` varre tudo, ao custo do
# tempo.
#
#     python -m pln.comparativo_modelos
#     python -m pln.comparativo_modelos --top-pre 20 --k 10

from __future__ import annotations

import argparse
import dataclasses
import itertools
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from pln.ajuste_fino import carregar_candidatos_de_texto
from pln.caminhos import DATASET_PADRAO, DATASET_TESTE, garantir_dir_de_resultados
from pln.classificador import (
    MAX_ITER_PADRAO,
    SEMENTE,
    carregar_dataset,
    construir_classificador,
)
from pln.experimento import REGUA_PADRAO
from pln.intencao import INTENCAO_FORA_DO_CATALOGO, aplicar_limiar_em_lote
from pln.metricas import (
    META_ACEITACAO_INDEVIDA,
    META_COBERTURA,
    META_F1_MACRO,
    ResultadoRNF03,
    avaliar_rnf03,
    curva_do_limiar,
    distancia_do_requisito,
    escolher_limiar,
    limiar_menos_distante,
    prever_com_modelo,
    prever_por_validacao_cruzada,
)
from pln.preprocessamento import ConfigPreprocessamento
from pln.vetorizacao import ConfigVetorizacao, todas_as_vetorizacoes


@dataclass(frozen=True)
class Candidato:
    nome: str
    estimador: object
    porque: str
    # A grade de hiperparâmetros DA FAMÍLIA, porque cada uma tem os seus e não
    # existe eixo comum: `alpha` do Naive Bayes e `C` de uma SVM não são a
    # mesma coisa com nomes diferentes.
    #
    # Sem isto, a comparação media famílias em configuração padrão — e o
    # padrão é um chute razoável do scikit-learn, não o ótimo de cada uma.
    # `ajuste_fino.py` só sabe buscar `alpha`/`fit_prior`, que são do Naive
    # Bayes: o pipeline estava completo para ele e incompleto para os demais.
    grade: tuple[tuple[str, tuple], ...] = ()

    # Qual ranking de pré-processamento esta família lê — o dela própria, e não
    # o de outra. Ver `experimento.REGUAS`.
    regua: str = REGUA_PADRAO


# A referência vem primeiro de propósito: toda linha abaixo dela é lida como
# diferença em relação ao que está em produção hoje.
# AS QUATRO FAMÍLIAS DO PARECER.
#
# `LogisticRegression`, `LinearSVC` e `SGDClassifier` foram nomeadas pelo
# parecer da Sprint 3; `MultinomialNB` entra como linha de base histórica, por
# ter sido o produto até então.
#
# `ComplementNB`, `RandomForest` e a rede neural saíram desta rodada. Foram
# medidas — os números ficam na Seção 3.3.7 — e nenhuma delas se aproximou das
# líderes. Mantê-las custaria varredura exaustiva própria para cada uma, e
# varredura exaustiva é o que esta rodada passou a exigir de todo competidor.
#
# `regua` é o ranking de texto que cada uma lê: o DELA PRÓPRIA. É a correção
# central desta rodada — antes todas herdavam o ranking do Naive Bayes, e uma
# família cujo texto ideal estivesse na posição 800 desse ranking nunca o veria.
def candidatos() -> list[Candidato]:
    return [
        Candidato(
            "LinearSVC calibrado",
            CalibratedClassifierCV(
                LinearSVC(random_state=SEMENTE), method="sigmoid", cv=3
            ),
            "referência: é o modelo em produção desde a Sprint 3",
            # `estimator__C` e não `C`: o parâmetro mora no LinearSVC que o
            # calibrador embrulha.
            grade=(("estimator__C", (0.1, 0.5, 1.0, 5.0, 10.0)),),
            regua="linearsvc",
        ),
        Candidato(
            "LogisticRegression",
            # BASE NEUTRA, e não `C=C_PADRAO`. Partir do valor que está em
            # produção tornaria a busca CIRCULAR: o estágio 2 procuraria o
            # melhor texto sob um hiperparâmetro que a busca anterior escolheu,
            # e o resultado dependeria do estado do repositório em vez de só do
            # dataset. Quem clonar o projeto precisa obter a mesma tabela.
            LogisticRegression(max_iter=MAX_ITER_PADRAO, random_state=SEMENTE),
            "venceu o comparativo da Sprint 3 e foi o produto por uma rodada",
            grade=(("C", (0.1, 0.5, 1.0, 5.0, 10.0)),),
            regua="logisticregression",
        ),
        Candidato(
            "MultinomialNB",
            # Base neutra, pela mesma razão: `ALPHA_PADRAO` saiu do
            # `ajuste_fino.py` e reintroduziria a circularidade.
            MultinomialNB(),
            "linha de base histórica: foi o produto até a Sprint 3, e segue sendo a régua",
            grade=(("alpha", (0.01, 0.1, 0.5, 1.0, 2.0)), ("fit_prior", (True, False))),
            regua="multinomialnb",
        ),
        Candidato(
            "SGD modified_huber",
            SGDClassifier(
                loss="modified_huber", random_state=SEMENTE, max_iter=2000, tol=1e-4
            ),
            "probabilidade nativa com custo de treino baixo",
            grade=(("alpha", (1e-5, 1e-4, 1e-3, 1e-2)),),
            regua="sgd",
        ),
    ]


@dataclass(frozen=True)
class Medicao:
    candidato: Candidato
    # O texto sob o qual esta família foi medida. Sem isto, a tabela final não
    # teria como mostrar que famílias diferentes preferem textos diferentes —
    # que é a razão de a busca ser conjunta.
    combinacao: Combinacao | None
    sem_rejeicao: ResultadoRNF03
    melhor_ponto: ResultadoRNF03
    tem_ponto_aprovado: bool
    segundos: float
    # F1 por intenção NO PONTO DE OPERAÇÃO, e não sobre o argmax cru: é o que
    # o sistema de fato faria. O agregado diz QUANTO uma família ganha; só a
    # abertura por classe diz ONDE — e é essa a pergunta interessante, porque
    # uma família pode ganhar na média e perder justamente na classe que o
    # requisito mais cobra.
    f1_por_intencao: dict[str, float]


# Uma célula do espaço de busca: família x texto x vetorização.
@dataclass(frozen=True)
class Combinacao:
    candidato: Candidato
    config_pre: ConfigPreprocessamento
    config_vet: ConfigVetorizacao
    # Vazio no estágio 2 (todos no padrão, comparação justa entre famílias);
    # preenchido no estágio 3, já sobre o melhor texto de cada uma.
    parametros: tuple[tuple[str, object], ...] = ()

    def descrever_parametros(self) -> str:
        if not self.parametros:
            return "padrão"
        return ", ".join(f"{nome.split('__')[-1]}={valor!r}" for nome, valor in self.parametros)

    def descrever_texto(self) -> str:
        return f"{self.config_vet.descrever()} | {self.config_pre.descrever()}"

    # A descrição carrega `|`, que é separador de célula em markdown: sem
    # escapar, a linha inteira da tabela se parte em colunas fantasmas.
    def descrever_texto_para_tabela(self) -> str:
        return self.descrever_texto().replace("|", "\\|")


# Um dicionário por família, e não uma lista única: é o que materializa
# "cada uma varre o ranking dela". Receber o dicionário pronto — em vez de
# lê-lo aqui — mantém a função testável sem tocar em disco.
def espaco_de_busca(
    configs_por_familia: dict[str, list[ConfigPreprocessamento]],
) -> list[Combinacao]:
    faltando = [c.nome for c in candidatos() if c.nome not in configs_por_familia]
    if faltando:
        raise KeyError(
            f"sem configurações de texto para {', '.join(faltando)}. Cada família "
            f"precisa das dela; herdar as de outra é a assimetria que esta busca desfaz."
        )
    return [
        Combinacao(candidato, config_pre, config_vet)
        for candidato in candidatos()
        for config_pre in configs_por_familia[candidato.nome]
        for config_vet in todas_as_vetorizacoes()
    ]


# Lê de disco o ranking de cada família. Separado de `espaco_de_busca` porque
# tocar em arquivo e montar o produto cartesiano são responsabilidades
# distintas, e só a segunda precisa ser exercitada por teste unitário.
def carregar_textos_por_familia(
    quantos: int,
) -> tuple[dict[str, list[ConfigPreprocessamento]], list[str]]:
    por_familia: dict[str, list[ConfigPreprocessamento]] = {}
    procedencias: list[str] = []
    for candidato in candidatos():
        configs, procedencia = carregar_candidatos_de_texto(quantos, candidato.regua)
        por_familia[candidato.nome] = configs
        procedencias.append(f"  {candidato.nome}: {procedencia.splitlines()[0]}")
    return por_familia, procedencias


def medir(
    combinacao: Combinacao, textos: list[str], rotulos: list[str], k: int
) -> Medicao:
    candidato = combinacao.candidato
    estimador = clone(candidato.estimador)
    if combinacao.parametros:
        estimador.set_params(**dict(combinacao.parametros))
    modelo = construir_classificador(
        config_pre=combinacao.config_pre,
        config_vet=combinacao.config_vet,
        estimador=estimador,
    )

    inicio = time.perf_counter()
    previstos, confiancas = prever_por_validacao_cruzada(textos, rotulos, modelo=modelo, k=k)
    segundos = time.perf_counter() - inicio

    curva = curva_do_limiar(rotulos, previstos, confiancas)
    aprovado = escolher_limiar(curva)
    ponto = aprovado or limiar_menos_distante(curva)

    classes = sorted(set(rotulos) | {INTENCAO_FORA_DO_CATALOGO})
    com_rejeicao = aplicar_limiar_em_lote(previstos, confiancas, ponto.limiar)
    por_classe = f1_score(
        rotulos, com_rejeicao, average=None, labels=classes, zero_division=0
    )

    return Medicao(
        candidato=candidato,
        combinacao=combinacao,
        sem_rejeicao=avaliar_rnf03(rotulos, previstos, confiancas, limiar=0.0),
        melhor_ponto=ponto,
        tem_ponto_aprovado=aprovado is not None,
        segundos=segundos,
        f1_por_intencao=dict(zip(classes, (float(v) for v in por_classe), strict=True)),
    )


def _tabela(medicoes: list[Medicao]) -> list[str]:
    linhas = [
        "| Modelo | F1 sem rejeição | Melhor limiar | F1 | Cobertura | Aceitação indevida | Atende | Tempo |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: |",
    ]
    for m in medicoes:
        p = m.melhor_ponto
        linhas.append(
            f"| {m.candidato.nome} | {m.sem_rejeicao.f1_macro:.4f} | {p.limiar:.2f} "
            f"| {p.f1_macro:.4f} | {p.cobertura:.1%} | {p.aceitacao_indevida:.1%} "
            f"| {'sim' if m.tem_ponto_aprovado else '—'} | {m.segundos:.1f}s |"
        )
    return linhas


# O ranking é pela DISTÂNCIA ATÉ O REQUISITO no ponto de operação, e não pelo
# F1 sem rejeição.
#
# São coisas diferentes e a diferença decide. O F1 sem rejeição ignora as duas
# métricas que o RNF03 exige junto, e o ponto de operação é o que o sistema de
# fato faria. Um modelo pode ter F1 bruto maior e servir menos gente.
# ESTÁGIO 3: os hiperparâmetros de cada família, no MELHOR TEXTO dela.
#
# Não no produto cartesiano com os textos: o espaço viraria
# famílias x textos x vetorizações x grade, e a grade da rede neural sozinha
# multiplicaria por seis um estágio que já leva meio minuto por medição. É a
# mesma economia em estágios que `ajuste_fino.py` faz, com a mesma limitação
# declarada — o ótimo conjunto de (texto, hiperparâmetro) pode estar fora.
#
# Devolve a melhor entre o padrão e as variantes: se a grade não render, o
# padrão permanece, e o relatório mostra isso em vez de esconder.
def variantes_de_hiperparametro(medicao: Medicao) -> list[Combinacao]:
    base = medicao.combinacao
    if base is None or not base.candidato.grade:
        return []

    nomes = [nome for nome, _ in base.candidato.grade]
    valores = [vals for _, vals in base.candidato.grade]
    return [
        dataclasses.replace(base, parametros=tuple(zip(nomes, combo, strict=True)))
        for combo in itertools.product(*valores)
    ]


# Entre todas as combinações de uma família, a melhor é a de MENOR distância
# até o RNF03 no ponto de operação — a mesma régua que ordena a tabela
# agregada. Ordenar por F1 bruto daria a vitória a quem serve menos gente.
def melhor_por_familia(medicoes: list[Medicao]) -> list[Medicao]:
    por_nome: dict[str, Medicao] = {}
    for m in medicoes:
        atual = por_nome.get(m.candidato.nome)
        if atual is None or distancia_do_requisito(m.melhor_ponto) < distancia_do_requisito(
            atual.melhor_ponto
        ):
            por_nome[m.candidato.nome] = m
    # A ordem dos candidatos é significativa: a referência vem primeiro.
    return [por_nome[c.nome] for c in candidatos() if c.nome in por_nome]


# A tabela que responde à pergunta do parecer: famílias diferentes preferem
# textos diferentes, ou o texto escolhido pelo Naive Bayes serve a todas?
def _tabela_de_textos(medicoes: list[Medicao]) -> list[str]:
    linhas = [
        "| Modelo | Melhor texto encontrado | Hiperparâmetros | F1 | Cobertura | Aceitação indevida |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for m in medicoes:
        texto = m.combinacao.descrever_texto_para_tabela() if m.combinacao else "(padrão)"
        params = m.combinacao.descrever_parametros() if m.combinacao else "padrão"
        p = m.melhor_ponto
        linhas.append(
            f"| {m.candidato.nome} | `{texto}` | {params} | {p.f1_macro:.4f} "
            f"| {p.cobertura:.1%} | {p.aceitacao_indevida:.1%} |"
        )

    textos_distintos = {m.combinacao.descrever_texto() for m in medicoes if m.combinacao}
    if len(textos_distintos) == 1:
        leitura = (
            "**Todas as famílias preferiram o MESMO texto.** Nesse caso a premissa que "
            "`ajuste_fino.py` assume — o classificador não ser eixo de busca — não custou "
            "nada, e medir as famílias sobre a configuração do `MultinomialNB` teria dado "
            "a mesma resposta."
        )
    else:
        leitura = (
            f"**As famílias preferiram {len(textos_distintos)} textos diferentes.** É a "
            "evidência de que medir todas sobre a configuração escolhida pelo "
            "`MultinomialNB` daria vantagem indevida a ele: o pré-processamento não é "
            "neutro entre famílias, e tratá-lo como constante escondia parte da diferença."
        )
    return linhas + ["", leitura, ""]


# TESTE PAREADO ENTRE OS DOIS PRIMEIROS.
#
# A tabela ordena, mas ordenar não é o mesmo que separar. Uma diferença de
# 0,015 de F1 entre duas famílias pode ser efeito real ou sorteio das dobras, e
# a decisão de trocar o modelo do produto não deveria depender de qual das duas
# possibilidades é a verdadeira sem alguém ter olhado.
#
# O pareamento é o que dá poder ao teste: os dois candidatos veem EXATAMENTE as
# mesmas partições, então a variação entre dobras — que é grande — se cancela na
# diferença. Comparar duas médias independentes exigiria uma amostra muito maior
# para detectar o mesmo efeito.
#
# REPETIÇÃO, E NÃO SÓ DOBRAS — a correção que este módulo já errou uma vez.
#
# Com 10 dobras, a comparação entre os dois primeiros devolveu t = 1,502 e foi
# lida como empate. Não era: com 10 dobras x 5 repetições, os mesmos dois
# modelos dão t = 3,527, e a diferença é real (intervalo de 95% da diferença
# [+0,0069, +0,0240], que não inclui zero).
#
# "Não significativo" com poucas medições significa NÃO CONSEGUI DETECTAR, e
# não "são iguais" — e as duas leituras levam a decisões opostas. Tratar falta
# de poder como empate autoriza escolher por critério de engenharia um modelo
# que a medição, com amostra suficiente, reprovaria.
#
# Cinco repetições custam minutos num relatório que roda raramente. É barato
# perto de trocar o modelo do produto pelo pior dos dois.
REPETICOES_PAREADAS = 5

_T_CRITICO_5_PORCENTO = {9: 2.262, 19: 2.093, 29: 2.045, 49: 2.010, 99: 1.984}


@dataclass(frozen=True)
class Pareado:
    nome_a: str
    nome_b: str
    por_dobra_a: list[float]
    por_dobra_b: list[float]

    @property
    def diferencas(self) -> list[float]:
        return [b - a for a, b in zip(self.por_dobra_a, self.por_dobra_b, strict=True)]

    @property
    def t(self) -> float:
        d = np.array(self.diferencas)
        desvio = d.std(ddof=1)
        if desvio == 0:
            return 0.0
        return float(d.mean() / (desvio / np.sqrt(len(d))))

    @property
    def significativo(self) -> bool:
        gl = len(self.diferencas) - 1
        # O valor crítico cai com os graus de liberdade; acima de 100 o t se
        # aproxima da normal e 1,96 basta. Interpolar seria precisão falsa.
        critico = _T_CRITICO_5_PORCENTO.get(gl, 1.96 if gl > 99 else 2.1)
        return abs(self.t) > critico

    # O intervalo diz QUANTO, e não apenas "sim ou não". Um resultado
    # significativo cujo intervalo vai de +0,001 a +0,003 é real e irrelevante.
    @property
    def intervalo_95(self) -> tuple[float, float]:
        d = np.array(self.diferencas)
        margem = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
        return float(d.mean() - margem), float(d.mean() + margem)


# O modelo que uma combinação descreve. Extraído porque três lugares o montam —
# a medição, a comparação pareada e a confirmação no retido — e montá-lo
# diferente em algum deles compararia coisas que não são a mesma.
def modelo_de(combinacao: Combinacao):
    estimador = clone(combinacao.candidato.estimador)
    if combinacao.parametros:
        estimador.set_params(**dict(combinacao.parametros))
    return construir_classificador(
        config_pre=combinacao.config_pre,
        config_vet=combinacao.config_vet,
        estimador=estimador,
    )


# As notas de UMA família sobre as partições repetidas.
#
# SEPARADO DA COMPARAÇÃO DE PROPÓSITO. Com quatro famílias há seis pares, e
# comparar par a par re-treinando cada vez custaria três vezes mais do que
# medir cada família uma vez. Mais importante que o custo: `RepeatedStratified
# KFold` com a mesma semente gera a MESMA sequência de partições para todas as
# chamadas, então as notas de famílias medidas separadamente continuam pareadas
# — é essa propriedade que autoriza derivar os seis pares por aritmética.
def medir_repetido(
    medicao: Medicao, textos: list[str], rotulos: list[str],
    k: int = 10, repeticoes: int = REPETICOES_PAREADAS,
) -> list[float]:
    if medicao.combinacao is None:
        return []

    X, y = np.array(textos, dtype=object), np.array(rotulos)
    dobras = RepeatedStratifiedKFold(
        n_splits=k, n_repeats=repeticoes, random_state=SEMENTE
    )

    notas: list[float] = []
    for treino, teste in dobras.split(X, y):
        modelo = modelo_de(medicao.combinacao)
        modelo.fit(list(X[treino]), list(y[treino]))
        notas.append(
            float(f1_score(list(y[teste]), list(modelo.predict(list(X[teste]))),
                           average="macro", zero_division=0))
        )
    return notas


# `Pareado` recebe os dois NOMES e depois as duas séries; a assinatura aqui
# intercala nome e série porque é assim que se lê no ponto de chamada.
def comparar_notas(
    nome_a: str, notas_a: list[float], nome_b: str, notas_b: list[float]
) -> Pareado:
    if len(notas_a) != len(notas_b):
        raise ValueError(
            "séries de tamanhos diferentes não são pareáveis: o teste pressupõe que "
            "a i-ésima nota das duas veio da MESMA partição."
        )
    return Pareado(nome_a, nome_b, list(notas_a), list(notas_b))


def comparar_pareado(
    a: Medicao, b: Medicao, textos: list[str], rotulos: list[str],
    k: int = 10, repeticoes: int = REPETICOES_PAREADAS,
) -> Pareado | None:
    if a.combinacao is None or b.combinacao is None:
        return None

    notas_a = medir_repetido(a, textos, rotulos, k, repeticoes)
    notas_b = medir_repetido(b, textos, rotulos, k, repeticoes)
    return comparar_notas(a.candidato.nome, notas_a, b.candidato.nome, notas_b)


def _secao_pareada(p: Pareado | None) -> list[str]:
    if p is None:
        return []

    d = np.array(p.diferencas)
    vitorias = int((d > 0).sum())
    linhas = [
        "## Os dois primeiros estão mesmo separados?",
        "",
        f"Ordenar não é separar. `{p.nome_b}` aparece à frente de `{p.nome_a}` na tabela,",
        "mas a diferença pode ser efeito real ou sorteio das dobras — e trocar o modelo do",
        "produto por um terceiro decimal que não se sustenta seria o pior dos dois erros.",
        "",
        f"Validação cruzada de 10 dobras REPETIDA {REPETICOES_PAREADAS} vezes com partições",
        f"diferentes — {len(d)} comparações, e as MESMAS partições para os dois modelos. O",
        "pareamento cancela a variação entre dobras, que é grande, e deixa só a diferença.",
        "",
        "A repetição não é zelo: com 10 dobras apenas, esta mesma comparação devolveu",
        "t = 1,502 e foi lida como empate. Poucas medições produzem 'não detectei', que não",
        "é 'são iguais' — e as duas leituras levam a decisões opostas.",
        "",
        f"| | `{p.nome_a}` | `{p.nome_b}` | Diferença |",
        "| --- | ---: | ---: | ---: |",
        f"| média das {len(d)} medições | {np.mean(p.por_dobra_a):.4f} "
        f"| {np.mean(p.por_dobra_b):.4f} | **{d.mean():+.4f}** |",
        f"| desvio | {np.std(p.por_dobra_a, ddof=1):.4f} "
        f"| {np.std(p.por_dobra_b, ddof=1):.4f} | {d.std(ddof=1):.4f} |",
        "",
        f"`{p.nome_b}` venceu em **{vitorias} de {len(d)}**. Teste t pareado: "
        f"**t = {p.t:.3f}** com {len(d) - 1} graus de liberdade. Intervalo de 95% da "
        f"diferença: **[{p.intervalo_95[0]:+.4f}, {p.intervalo_95[1]:+.4f}]**.",
        "",
    ]

    if p.significativo:
        linhas += [
            f"**A diferença é significativa a 5%, e o intervalo não inclui zero.** "
            f"`{p.nome_b}` separa-se de `{p.nome_a}` de forma que não se explica por sorteio "
            f"de partições.",
            "",
            "A consequência é direta: **o desempate por critério de engenharia deixa de ser "
            "legítimo aqui**. Latência e simplicidade de manutenção decidem entre modelos "
            "equivalentes; diante de uma diferença medida, escolher o de baixo é escolher o "
            "pior de propósito. Se o custo de engenharia do vencedor for inaceitável, isso "
            "precisa ser argumentado como tal, e não disfarçado de empate técnico.",
            "",
        ]
    else:
        linhas += [
            "**A diferença está dentro do ruído.** As duas famílias são estatisticamente "
            "indistinguíveis sobre este corpus, e a tabela acima não autoriza dizer que uma "
            "é melhor que a outra.",
            "",
            "Isso é resultado, e não ausência dele: o empate é o que AUTORIZA decidir por "
            "latência, explicabilidade e simplicidade de manutenção em vez de por um terceiro "
            "decimal. Um critério de engenharia aplicado sobre um empate medido é defensável; "
            "aplicado sobre uma diferença real, seria escolher o pior modelo de propósito.",
            "",
        ]
    return linhas


# TODOS OS PARES, e não só os dois primeiros.
#
# Saber que a líder se separa da segunda não diz se ela se separa da terceira e
# da quarta. Com quatro famílias são seis pares, e derivá-los das quatro séries
# já medidas custa aritmética — re-treinar por par custaria três vezes mais.
def todos_os_pares(
    notas_por_familia: dict[str, list[float]]
) -> list[Pareado]:
    nomes = list(notas_por_familia)
    return [
        comparar_notas(a, notas_por_familia[a], b, notas_por_familia[b])
        for a, b in itertools.combinations(nomes, 2)
    ]


def _secao_todos_os_pares(pares: list[Pareado]) -> list[str]:
    if not pares:
        return []

    linhas = [
        "## Todos os pares, dois a dois",
        "",
        f"Validação cruzada de 10 dobras repetida {REPETICOES_PAREADAS} vezes — "
        f"{len(pares[0].diferencas)} medições por família, todas sobre as MESMAS partições.",
        "Cada família foi medida uma vez; os pares saem por aritmética sobre essas notas.",
        "",
        "| Par | Diferença média | t | IC 95% | Separáveis? |",
        "| --- | ---: | ---: | --- | :---: |",
    ]
    for p in pares:
        d = np.array(p.diferencas)
        baixo, alto = p.intervalo_95
        marca = "**sim**" if p.significativo else "não"
        linhas.append(
            f"| `{p.nome_b}` − `{p.nome_a}` | {d.mean():+.4f} | {p.t:+.3f} "
            f"| [{baixo:+.4f}, {alto:+.4f}] | {marca} |"
        )

    separaveis = sum(1 for p in pares if p.significativo)
    return linhas + [
        "",
        f"**{separaveis} de {len(pares)}** pares se separam a 5%. Um par que NÃO se separa "
        "não autoriza dizer que uma das duas é melhor — só que esta amostra não conseguiu "
        "distingui-las, que é coisa diferente de serem iguais.",
        "",
    ]


# CONFIRMAÇÃO NO CONJUNTO RETIDO.
#
# Tudo acima é medido no desenvolvimento, e o desenvolvimento escolheu o texto,
# o hiperparâmetro e o limiar. Escolher o máximo entre 11.884 estimativas de
# validação cruzada é otimista por construção — as quatro famílias pagam esse
# otimismo igualmente, o que preserva a COMPARAÇÃO entre elas, mas infla o
# número ABSOLUTO de todas.
#
# O retido é o que corrige isso, e só funciona se três coisas forem respeitadas:
#
#   1. o limiar é calibrado SÓ no desenvolvimento e entra aqui congelado;
#   2. o modelo é treinado no desenvolvimento INTEIRO, e não numa dobra;
#   3. o retido é lido UMA VEZ por família, nunca em laço de busca.
#
# Quebrar a primeira é a mais fácil e a mais silenciosa: bastaria chamar
# `curva_do_limiar` sobre o retido para o número melhorar e deixar de significar
# alguma coisa.
def confirmar_no_retido(
    medicao: Medicao,
    dev_textos: list[str],
    dev_rotulos: list[str],
    ret_textos: list[str],
    ret_rotulos: list[str],
    k: int = 5,
) -> tuple[ResultadoRNF03, float] | None:
    if medicao.combinacao is None:
        return None

    # 1. limiar calibrado no DESENVOLVIMENTO.
    previstos, confiancas = prever_por_validacao_cruzada(
        dev_textos, dev_rotulos, modelo=modelo_de(medicao.combinacao), k=k
    )
    curva = curva_do_limiar(dev_rotulos, previstos, confiancas)
    ponto = escolher_limiar(curva) or limiar_menos_distante(curva)

    # 2. treino no desenvolvimento inteiro; 3. uma leitura do retido.
    modelo = modelo_de(medicao.combinacao)
    modelo.fit(dev_textos, dev_rotulos)
    prev, conf = prever_com_modelo(modelo, ret_textos)
    return avaliar_rnf03(ret_rotulos, prev, conf, ponto.limiar), ponto.limiar


def _secao_retido(confirmacoes: list[tuple[Medicao, ResultadoRNF03, float]]) -> list[str]:
    if not confirmacoes:
        return []

    linhas = [
        "## Confirmação no teste retido",
        "",
        "Cada família treinada no desenvolvimento inteiro e medida **uma única vez** no",
        "conjunto retido, com o limiar congelado do desenvolvimento. Os números da tabela",
        "acima são otimistas por construção — escolhem o máximo entre milhares de",
        "estimativas —, e é aqui que se vê quanto desse otimismo sobrevive.",
        "",
        "| Modelo | Limiar | F1 | Cobertura | Aceit. indevida | Atende aos 3 |",
        "| --- | ---: | ---: | ---: | ---: | :---: |",
    ]
    for medicao, r, limiar in confirmacoes:
        marca = "**sim**" if r.aprovado else "—"
        linhas.append(
            f"| {medicao.candidato.nome} | {limiar:.2f} | {r.f1_macro:.4f} "
            f"| {r.cobertura:.1%} | {r.aceitacao_indevida:.1%} | {marca} |"
        )

    aprovadas = [m.candidato.nome for m, r, _ in confirmacoes if r.aprovado]
    linhas += [
        "",
        f"Retido: {confirmacoes[0][1].conhecidos + confirmacoes[0][1].fora_do_catalogo} "
        f"exemplos, dos quais {confirmacoes[0][1].fora_do_catalogo} de `fora_do_catalogo`.",
        "",
    ]
    if aprovadas:
        linhas += [
            f"**Atende aos três limites do RNF03 no retido:** {', '.join(aprovadas)}.",
            "",
            "Atender aqui não é o mesmo que cumprir o requisito. O conjunto retido é uma",
            "separação interna do corpus, feita pela mesma equipe que o escreveu; a Seção 6.3",
            "exige frases novas e custodiadas por quem não participa do ajuste. Além disso,",
            "com pouco mais de duzentos exemplos o intervalo de confiança do F1 é largo —",
            "a estimativa pontual pode passar de 0,85 com o intervalo incluindo valores que",
            "não passam.",
            "",
        ]
    else:
        linhas += ["**Nenhuma família atende aos três limites no retido.**", ""]
    return linhas


# Padrão CONTRA ajustado, lado a lado.
#
# Sem esta tabela o relatório pode parecer contraditório: a escolha é pela
# menor distância até o RNF03, não pelo maior F1, então uma família pode
# aparecer com F1 MENOR depois de ajustada — porque trocou F1 por cobertura e
# chegou mais perto do requisito. Mostrar as duas linhas é o que torna a
# decisão verificável em vez de misteriosa.
def _tabela_de_hiperparametros(
    no_padrao: list[Medicao], ajustadas: list[Medicao]
) -> list[str]:
    por_nome = {m.candidato.nome: m for m in no_padrao}
    linhas = [
        "| Modelo | Hiperparâmetros | F1 | Cobertura | Aceit. indevida | Distância até o RNF03 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    mudaram = 0
    for m in ajustadas:
        base = por_nome[m.candidato.nome]
        params = m.combinacao.descrever_parametros() if m.combinacao else "padrão"
        if params == "padrão":
            p = m.melhor_ponto
            linhas.append(
                f"| {m.candidato.nome} | padrão (a grade não superou) | {p.f1_macro:.4f} "
                f"| {p.cobertura:.1%} | {p.aceitacao_indevida:.1%} "
                f"| {distancia_do_requisito(p):.3f} |"
            )
            continue

        mudaram += 1
        b, a = base.melhor_ponto, m.melhor_ponto
        linhas.append(
            f"| {m.candidato.nome} | padrão | {b.f1_macro:.4f} | {b.cobertura:.1%} "
            f"| {b.aceitacao_indevida:.1%} | {distancia_do_requisito(b):.3f} |"
        )
        linhas.append(
            f"| | **{params}** | **{a.f1_macro:.4f}** | **{a.cobertura:.1%}** "
            f"| **{a.aceitacao_indevida:.1%}** | **{distancia_do_requisito(a):.3f}** |"
        )

    return linhas + [
        "",
        f"A grade mudou a escolha em **{mudaram} de {len(ajustadas)}** famílias. Nas demais, o "
        "padrão do scikit-learn já era o melhor ponto da grade — o que é informação, e não "
        "ausência de resultado.",
        "",
        "**A escolha é pela menor distância até o RNF03, e não pelo maior F1.** Por isso uma "
        "família pode aparecer com F1 MENOR depois de ajustada: trocou F1 por cobertura e "
        "chegou mais perto de atender aos três limites simultaneamente, que é o que o "
        "requisito cobra. Ordenar por F1 sozinho premiaria quem serve menos gente.",
        "",
    ]


# A abertura por classe é o que transforma "ganha por +0,044" em uma afirmação
# inspecionável. Uma família pode vencer na média e perder na classe que mais
# importa — `fora_do_catalogo` sustenta sozinha a aceitação indevida do RNF03,
# e o agregado esconderia isso.
def _tabela_por_intencao(medicoes: list[Medicao]) -> list[str]:
    intencoes = sorted(medicoes[0].f1_por_intencao)
    cabecalho = "| Intenção | " + " | ".join(m.candidato.nome for m in medicoes) + " | Melhor |"
    separador = "| --- | " + " | ".join("---:" for _ in medicoes) + " | --- |"

    linhas = [cabecalho, separador]
    vitorias: dict[str, int] = {}
    for intencao in intencoes:
        valores = [m.f1_por_intencao[intencao] for m in medicoes]
        topo = max(valores)
        vencedora = medicoes[valores.index(topo)].candidato.nome
        vitorias[vencedora] = vitorias.get(vencedora, 0) + 1
        celulas = " | ".join(
            (f"**{v:.3f}**" if v == topo else f"{v:.3f}") for v in valores
        )
        linhas.append(f"| `{intencao}` | {celulas} | {vencedora} |")

    placar = ", ".join(f"{nome} em {n}" for nome, n in
                       sorted(vitorias.items(), key=lambda x: -x[1]))
    return linhas + [
        "",
        f"Placar por intenção: {placar}.",
        "",
        "A leitura por linha importa mais que o placar. Uma família que vence em muitas "
        "intenções fáceis e perde em `fora_do_catalogo` piora a aceitação indevida do "
        "RNF03, que é medida só sobre essa classe.",
        "",
    ]


def _leitura(medicoes: list[Medicao], pareado: Pareado | None = None) -> list[str]:
    referencia = medicoes[0]
    melhor = min(medicoes, key=lambda m: distancia_do_requisito(m.melhor_ponto))

    if melhor.candidato.nome == referencia.candidato.nome:
        return [
            "## Leitura",
            "",
            "**A referência continua sendo a melhor.** Nenhuma das famílias testadas chega",
            "mais perto do RNF03 que o `MultinomialNB` sobre este corpus, então não há troca",
            "a considerar e a Seção 3.3.2 segue válida como está.",
            "",
            _nota_da_regua(),
            "",
        ]

    atual, novo_ponto = referencia.melhor_ponto, melhor.melhor_ponto
    distancia_atual = distancia_do_requisito(atual)
    distancia_nova = distancia_do_requisito(novo_ponto)

    comparacao = [
        "| Métrica | `MultinomialNB` | "
        f"`{melhor.candidato.nome}` | Diferença |",
        "| --- | ---: | ---: | ---: |",
        f"| F1-macro | {atual.f1_macro:.4f} | {novo_ponto.f1_macro:.4f} "
        f"| {novo_ponto.f1_macro - atual.f1_macro:+.4f} |",
        f"| Cobertura | {atual.cobertura:.1%} | {novo_ponto.cobertura:.1%} "
        f"| {novo_ponto.cobertura - atual.cobertura:+.1%} |",
        f"| Aceitação indevida | {atual.aceitacao_indevida:.1%} "
        f"| {novo_ponto.aceitacao_indevida:.1%} "
        f"| {novo_ponto.aceitacao_indevida - atual.aceitacao_indevida:+.1%} |",
        f"| Distância até o RNF03 | {distancia_atual:.3f} | {distancia_nova:.3f} "
        f"| {distancia_nova - distancia_atual:+.3f} |",
        "",
    ]

    empate = pareado is not None and not pareado.significativo
    if empate:
        veredito = (
            f"**`{melhor.candidato.nome}` lidera a tabela, mas o teste pareado não separa os "
            f"dois primeiros** (t = {pareado.t:.3f}, dentro do ruído). Não há base para dizer "
            f"que uma família é melhor que a outra sobre este corpus, e o desempate legítimo "
            f"passa a ser de engenharia: latência, explicabilidade e custo de manutenção."
        )
    elif melhor.tem_ponto_aprovado:
        veredito = (
            f"**`{melhor.candidato.nome}` atende aos três limites do RNF03, e a referência "
            f"não.** A troca se justifica sozinha."
        )
    else:
        veredito = (
            f"**Nenhum candidato atende ao RNF03 sobre este corpus, mas "
            f"`{melhor.candidato.nome}` chega bem mais perto.** É o que aparece na coluna de "
            f"diferença acima: a decisão não é entre cumprir e não cumprir o requisito, é "
            f"entre servir mais ou menos gente enquanto ele não é cumprido. Cobertura é "
            f"literalmente a proporção de perguntas legítimas que o sistema se dispõe a "
            f"responder."
        )

    return [
        "## Leitura",
        "",
        veredito,
        "",
        "Comparação no PONTO DE OPERAÇÃO de cada um, que é o que o sistema faria:",
        "",
        *comparacao,
        "**O que a troca ainda custa.** A busca conjunta removeu a maior parte do problema: "
        "cada família foi medida sobre o SEU melhor texto, e não sobre o que o "
        "`MultinomialNB` escolheu. O que sobra é o estágio 1 — quem RANQUEIA os textos "
        "continua sendo o `MultinomialNB`, e a busca só enxerga o topo desse ranking. Se o "
        "texto ideal de outra família estiver fora dele, este comparativo não o encontra. "
        "`--top-pre 0` elimina o resíduo ao custo do tempo.",
        "",
        "A Seção 3.3.2 precisa ser reescrita de qualquer forma ao adotar outra família: ela "
        "hoje sustenta a validade do pré-processamento no fato de régua e produto serem o "
        "mesmo modelo, e esse argumento deixa de valer.",
        "",
        _nota_da_regua(),
        "",
    ]


# Sem contagem embutida de propósito: o número de execuções da varredura muda
# com o dataset, e um literal aqui envelheceria em silêncio a cada ampliação do
# corpus — que é exatamente a classe de defeito que este projeto persegue.
def _nota_da_regua() -> str:
    return (
        "A varredura de `experimento.py` não muda de régua em nenhum cenário: são milhares "
        "de medições, e é a velocidade do `MultinomialNB` que as torna praticáveis. O número "
        "exato de execuções desta rodada está em `comparativo_preprocessamento.md`."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compara famílias de classificador sobre o mesmo pré-processamento."
    )
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--top-pre", type=int, default=8,
                        help="quantos pré-processamentos do relatório do experimento "
                             "entram na busca (0 = todos)")
    parser.add_argument(
        "--confirmar-no-retido", action="store_true",
        help="mede cada família UMA vez no conjunto retido, com o limiar congelado do "
             "desenvolvimento. Desligado por padrão: o retido é recurso escasso e não "
             "deve ser lido toda vez que alguém rodar o comparativo por outro motivo.",
    )
    parser.add_argument("--sem-hiperparametros", action="store_true",
                        help="pula o estágio 3 e compara todas as famílias em "
                             "configuração padrão")
    parser.add_argument("--salvar", type=Path, default=None)
    args = parser.parse_args(argv)

    textos, rotulos = carregar_dataset(args.dataset)
    configs_por_familia, procedencias = carregar_textos_por_familia(args.top_pre)
    espaco = espaco_de_busca(configs_por_familia)

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Validação cruzada de {args.k} dobras, semente {SEMENTE}")
    print("Ranking de texto de CADA família (e não o de uma só):")
    print("\n".join(procedencias))
    print(f"Espaço: {len(espaco)} medições\n")

    # Em paralelo porque o espaço cresce como produto, e as medições são
    # independentes: a semente é fixa, então a saída é idêntica em série.
    todas = Parallel(n_jobs=-1, verbose=5)(
        delayed(medir)(combinacao, textos, rotulos, args.k) for combinacao in espaco
    )
    no_padrao = melhor_por_familia(list(todas))

    # ESTÁGIO 3: a grade de cada família, sobre o melhor texto dela.
    variantes = [v for m in no_padrao for v in variantes_de_hiperparametro(m)]
    if variantes and not args.sem_hiperparametros:
        print(f"\nEstágio 3: {len(variantes)} variantes de hiperparâmetro\n")
        ajustadas = Parallel(n_jobs=-1, verbose=5)(
            delayed(medir)(v, textos, rotulos, args.k) for v in variantes
        )
        medicoes = melhor_por_familia(no_padrao + list(ajustadas))
    else:
        medicoes = no_padrao

    # Cada família medida UMA vez sobre as partições repetidas; os seis pares
    # saem por aritmética. Re-treinar por par custaria três vezes mais.
    print(f"\nMedindo {len(medicoes)} famílias em validação cruzada repetida...", flush=True)
    notas_por_familia = {
        m.candidato.nome: notas
        for m, notas in zip(
            medicoes,
            Parallel(n_jobs=-1, verbose=5)(
                delayed(medir_repetido)(m, textos, rotulos) for m in medicoes
            ),
            strict=True,
        )
    }
    pares = todos_os_pares(notas_por_familia)

    ordenadas = sorted(medicoes, key=lambda m: distancia_do_requisito(m.melhor_ponto))
    pareado = None
    if len(ordenadas) >= 2:
        pareado = comparar_notas(
            ordenadas[1].candidato.nome, notas_por_familia[ordenadas[1].candidato.nome],
            ordenadas[0].candidato.nome, notas_por_familia[ordenadas[0].candidato.nome],
        )

    confirmacoes: list[tuple[Medicao, ResultadoRNF03, float]] = []
    if args.confirmar_no_retido:
        print("\nConfirmando cada família no conjunto retido (uma leitura cada)...", flush=True)
        ret_textos, ret_rotulos = carregar_dataset(DATASET_TESTE)
        for m in ordenadas:
            resultado = confirmar_no_retido(m, textos, rotulos, ret_textos, ret_rotulos, args.k)
            if resultado is not None:
                confirmacoes.append((m, resultado[0], resultado[1]))

    linhas = [
        "# Comparativo de famílias de classificador",
        "",
        "Arquivo gerado por `python -m pln.comparativo_modelos`. Não editar à mão.",
        "",
        f"- Dataset: `{args.dataset.name}` ({len(textos)} exemplos)",
        f"- Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}",
        f"- Busca conjunta: {len(candidatos())} famílias, **{len(espaco)} medições**",
        "- Cada família lê o ranking de texto **dela própria**, produzido por",
        "  `python -m pln.experimento --regua <familia>` com ela como instrumento de medida.",
        "  Herdar o ranking de uma família favorece quem o produziu.",
        "- Escolher o máximo entre milhares de estimativas de validação cruzada é otimista",
        "  por construção. As quatro pagam esse otimismo igualmente, o que preserva a",
        "  comparação entre elas — mas infla o número absoluto de todas. É o conjunto",
        "  retido que corrige, e por isso `--confirmar-no-retido` existe.",
        "- Limites do RNF03: F1-macro ≥ "
        f"{META_F1_MACRO:.2f}, cobertura ≥ {META_COBERTURA:.0%}, "
        f"aceitação indevida ≤ {META_ACEITACAO_INDEVIDA:.0%}",
        "",
        "`Melhor limiar` é o ponto de operação que atende aos três limites; quando nenhum",
        "atende, é o que chega mais perto. `Tempo` é o custo da validação cruzada inteira,",
        "não de uma inferência.",
        "",
        *_tabela(medicoes),
        "",
        "## Cada família prefere o mesmo texto?",
        "",
        "Esta é a pergunta que medir todas sobre uma configuração fixa não responde. O",
        "pré-processamento não é neutro entre famílias de classificador: uma fronteira",
        "discriminativa e uma contagem por classe não pedem o mesmo texto.",
        "",
        *_tabela_de_textos(medicoes),
        "## O que o ajuste de hiperparâmetro mudou",
        "",
        "Terceiro estágio: a grade de cada família, sobre o melhor texto dela. Até esta",
        "rodada a comparação media todo mundo em configuração PADRÃO — e o padrão do",
        "scikit-learn é um chute razoável, não o ótimo de cada família. `ajuste_fino.py`",
        "só sabe buscar `alpha` e `fit_prior`, que são do Naive Bayes: o pipeline estava",
        "completo para ele e incompleto para os demais.",
        "",
        *_tabela_de_hiperparametros(no_padrao, medicoes),
        "## Onde cada família ganha",
        "",
        "F1 por intenção, no ponto de operação de cada família — que é o que o sistema de",
        "fato faria. O agregado da tabela acima diz *quanto* uma família ganha; esta diz",
        "*onde*, que é a pergunta que permite decidir se o ganho serve ao requisito.",
        "",
        *_tabela_por_intencao(medicoes),
        *_secao_todos_os_pares(pares),
        *_secao_pareada(pareado),
        *_secao_retido(confirmacoes),
        *_leitura(medicoes, pareado),
        "## Por que cada candidato entrou",
        "",
        *[f"- **{m.candidato.nome}** — {m.candidato.porque}" for m in medicoes],
        "",
    ]

    destino = args.salvar or (garantir_dir_de_resultados() / "comparativo_modelos.md")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print()
    for m in medicoes:
        params = m.combinacao.descrever_parametros() if m.combinacao else "padrão"
        print(
            f"  {m.candidato.nome:>22}: F1 {m.melhor_ponto.f1_macro:.4f}  "
            f"cob {m.melhor_ponto.cobertura:>5.1%}  |  {params}"
        )
    print(f"\nRelatório salvo em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
