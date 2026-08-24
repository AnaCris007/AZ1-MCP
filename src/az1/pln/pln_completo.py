# =============================================================================
# pln_completo.py — O pipeline inteiro de PLN em UM arquivo
# =============================================================================
# Consolidação de quatro módulos em um só. O conteúdo é o mesmo; o que muda é
# que não há mais import entre partes, e o arquivo roda sozinho:
#
#     preprocessamento.py  ->  SEÇÃO 1 — texto bruto vira tokens
#     vetorizacao.py       ->  SEÇÃO 2 — tokens viram matriz numérica
#     classificador.py     ->  SEÇÃO 3 — o modelo do produto
#     experimento.py       ->  SEÇÃO 4 — a busca pela melhor configuração
#                              SEÇÃO 5 — a linha de comando
#
# Os módulos originais continuam onde estavam e seguem funcionando. Este
# arquivo é uma cópia consolidada, não um substituto — mexer em um não mexe no
# outro, e é bom saber disso antes de corrigir um bug só aqui.
#
# O QUE PRECISOU MUDAR NA JUNÇÃO
# ------------------------------
# Dois nomes existiam em dois módulos com significados diferentes. Juntar os
# arquivos faz um apagar o outro em silêncio — o segundo `def` simplesmente
# sobrescreve o primeiro, sem erro nenhum —, então os dois foram renomeados
# para o que de fato fazem:
#
#   experimento.avaliar_com_validacao_cruzada   -> medir_configuracao
#       mede UMA configuração e devolve (F1 médio, desvio, vocabulário)
#
#   classificador.avaliar_com_validacao_cruzada -> avaliar_classificador
#       avalia UM modelo pronto e devolve (F1, relatório, matriz, classes)
#
# E os dois `main()` viraram um só, com subcomandos (SEÇÃO 5).
#
# Os arquivos de saída levam sufixo `_completo` de propósito: rodar este
# arquivo não sobrescreve os artefatos versionados que a versão modular gera.
#
# USO
# ---
#     python -m az1.pln.pln_completo treinar
#     python -m az1.pln.pln_completo prever "Quais prazos vencem esta semana?"
#     python -m az1.pln.pln_completo experimento --sem-ordem
#
# Também roda sem instalar o pacote, por não importar mais nada de `az1`:
#
#     python src/az1/pln/pln_completo.py treinar
#
# Dependências de dados, baixadas uma vez:
#     python -m nltk.downloader stopwords rslp
#     python -m spacy download pt_core_news_sm
# =============================================================================

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.naive_bayes import BernoulliNB, ComplementNB, MultinomialNB
from sklearn.pipeline import Pipeline

# -----------------------------------------------------------------------------
# Caminhos e constantes globais
# -----------------------------------------------------------------------------

AQUI = Path(__file__).resolve().parent
DATASET_PADRAO = AQUI / "dados" / "intencoes_exemplo.csv"
RESULTADOS_DIR = AQUI / "resultados"

# Sufixo `_completo` para não pisar nos arquivos que preprocessamento.py e
# companhia geram — os dois conjuntos convivem na mesma pasta.
MODELO_PADRAO = RESULTADOS_DIR / "classificador_completo.joblib"
RELATORIO_CSV = RESULTADOS_DIR / "comparativo_preprocessamento_completo.csv"
RELATORIO_MD = RESULTADOS_DIR / "comparativo_preprocessamento_completo.md"

# Semente fixa. Sem ela, as dobras da validação cruzada mudariam a cada
# execução e duas configurações não seriam comparáveis: parte da diferença
# entre elas seria sorteio diferente, não pré-processamento diferente.
SEMENTE = 42

# Largura das tabelas impressas no terminal.
LARGURA = 118


# =============================================================================
# SEÇÃO 1 — PRÉ-PROCESSAMENTO
# =============================================================================
# Três ideias sustentam esta seção:
#
# 1. Não existe conjunto de etapas universalmente melhor. O que ajuda num
#    corpus atrapalha noutro. Nenhuma etapa é obrigatória.
#
# 2. A ORDEM também não é dada. Trocar duas etapas de lugar muda o resultado —
#    e, em alguns casos, faz uma etapa parar de funcionar. Por isso a ordem é
#    campo da configuração, não decisão embutida na função.
#
# 3. A TOKENIZAÇÃO é uma escolha, não um detalhe. Separar por espaço, por regex
#    ou por regra linguística produz vocabulários diferentes a partir do mesmo
#    texto — e é o vocabulário que o classificador enxerga.
#
# Quem decide as três coisas é o experimento (SEÇÃO 4), comparando por métrica
# medida.
# =============================================================================

# Pontuação vira ESPAÇO, não vazio. Se virasse vazio, "prazo,marco" colaria em
# "prazomarco" e criaria um token que não existe em lugar nenhum do corpus.
_PONTUACAO = re.compile(r"[^\w\s]", flags=re.UNICODE)
_NUMEROS = re.compile(r"\d+")
_ESPACOS_REPETIDOS = re.compile(r"\s+")

# Nomes das etapas ordenáveis. A tupla também define a ORDEM PADRÃO.
#
# A tokenização NÃO está aqui de propósito: ela não é uma etapa que se
# intercala entre as outras, é a operação que converte texto em tokens — e
# acontece sempre que o pipeline precisa de tokens, além de uma vez ao final.
# Permutá-la não faria sentido; escolhê-la, sim, e por isso ela é um campo à
# parte da configuração.
ETAPAS: tuple[str, ...] = (
    "minusculas",
    "remover_acentos",
    "remover_pontuacao",
    "remover_numeros",
    "stopwords",
    "morfologia",
)


class ModoStopwords(StrEnum):
    # As três formas de tratar stopwords, comparáveis na mesma execução.
    #
    # As duas últimas costumam ser tratadas como a mesma coisa, e não são: a
    # lista do NLTK para português inclui "não", "nem", "sem" e "nunca". Em
    # classificação de ASSUNTO isso é inofensivo. Na nossa, de INTENÇÃO, essas
    # palavras carregam o sinal — "não atualizou o status" (alerta) e
    # "atualizou o status" (transação) viram a mesma frase se a negação sair.

    MANTER = "manter"
    REMOVER_TUDO = "remover_tudo"
    PRESERVAR_NEGACOES = "preservar_negacoes"


class ModoMorfologia(StrEnum):
    # Redução de palavras à forma base. As opções são EXCLUSIVAS entre si.
    #
    # STEMMING corta sufixos por regras mecânicas, sem dicionário e sem olhar o
    # contexto. Rápido e independente de modelo. Produz radicais que muitas
    # vezes não são palavras ("vencer" -> "venc") e junta demais.
    #
    # LEMATIZAÇÃO mapeia cada palavra para a forma de dicionário ("vencendo" ->
    # "vencer") usando classe gramatical e contexto. Resultado sempre é palavra
    # real e o agrupamento é mais preciso, mas exige modelo treinado e é uma
    # ordem de grandeza mais lenta.
    #
    # Aplicar os dois seria redundante e destrutivo — lematizar um radical não
    # tem sentido. Por isso são valores de um mesmo campo, e não duas flags.

    NENHUMA = "nenhuma"
    STEMMING = "stemming"
    LEMATIZACAO = "lematizacao"


class Tokenizacao(StrEnum):
    # Como o texto vira lista de tokens. Muda o que o vetorizador enxerga.
    #
    # SPLIT: `str.split()`. Corta em espaço em branco e mais nada. "prazo?" é
    # UM token, diferente de "prazo" — então pontuação grudada multiplica o
    # vocabulário. É o baseline: o mínimo possível.
    #
    # REGEX: `wordpunct_tokenize` do NLTK, que aplica `\w+|[^\w\s]+`. Separa
    # blocos de letras e dígitos de blocos de pontuação, então "prazo?" vira
    # ["prazo", "?"]. Independente de idioma e previsível, mas ingênuo com o
    # que não é palavra pura: "R$1.500,00" vira sete tokens.
    #
    # LINGUISTICO: o tokenizador do spaCy para português. Regras específicas do
    # idioma — prefixos, sufixos, infixos e tabela de exceções. Reconhece
    # abreviaturas, mantém números com separador decimal inteiros e trata
    # contrações como a gramática manda. Mais caro, e o único que sabe que está
    # lendo português.

    SPLIT = "split"
    REGEX = "regex"
    LINGUISTICO = "linguistico"


# Palavras de negação protegidas em ModoStopwords.PRESERVAR_NEGACOES.
# As variantes sem acento existem porque a etapa pode rodar depois da remoção
# de acentos, e a comparação é literal.
NEGACOES = frozenset(
    {"não", "nao", "nem", "sem", "nunca", "jamais", "nada", "ninguém", "ninguem", "nenhum", "nenhuma"}
)


# `frozen` porque a configuração vira chave de dicionário no experimento, e
# chave precisa ser imutável e hasheável.
@dataclass(frozen=True)
class ConfigPreprocessamento:
    minusculas: bool = False
    remover_acentos: bool = False
    remover_pontuacao: bool = False
    remover_numeros: bool = False
    stopwords: ModoStopwords = ModoStopwords.MANTER
    morfologia: ModoMorfologia = ModoMorfologia.NENHUMA
    tokenizacao: Tokenizacao = Tokenizacao.SPLIT
    ordem: tuple[str, ...] = ETAPAS

    def __post_init__(self) -> None:
        # A ordem precisa conter todas as etapas, e só elas. Validar aqui
        # transforma um erro silencioso — etapa que some da ordem e nunca roda —
        # em uma exceção no momento da construção.
        if set(self.ordem) != set(ETAPAS):
            faltando = set(ETAPAS) - set(self.ordem)
            sobrando = set(self.ordem) - set(ETAPAS)
            raise ValueError(f"ordem inválida — faltando {faltando or '{}'}, sobrando {sobrando or '{}'}")

    def etapa_esta_ligada(self, nome: str) -> bool:
        # Os dois campos de múltipla escolha têm um valor que significa
        # "desligada"; os demais são booleanos.
        if nome == "stopwords":
            return self.stopwords is not ModoStopwords.MANTER
        if nome == "morfologia":
            return self.morfologia is not ModoMorfologia.NENHUMA
        return bool(getattr(self, nome))

    def etapas_ativas_na_ordem(self) -> tuple[str, ...]:
        return tuple(nome for nome in self.ordem if self.etapa_esta_ligada(nome))

    # Usado pelo experimento ao varrer permutações de ordem.
    def copiar_com_outra_ordem(self, ordem: tuple[str, ...]) -> ConfigPreprocessamento:
        return replace(self, ordem=ordem)

    # Descrição legível para as tabelas de resultado.
    def descrever(self) -> str:
        nomes = []
        for etapa in self.etapas_ativas_na_ordem():
            if etapa == "stopwords":
                nomes.append(f"sw:{self.stopwords.value}")
            elif etapa == "morfologia":
                nomes.append(self.morfologia.value)
            else:
                nomes.append(etapa)
        etapas = " > ".join(nomes) if nomes else "(texto cru)"
        return f"[tok:{self.tokenizacao.value}] {etapas}"


# -----------------------------------------------------------------------------
# Tokenização
# -----------------------------------------------------------------------------


# `spacy.blank("pt")` carrega as REGRAS do idioma sem carregar modelo
# estatístico nenhum: nada de tagger, parser ou vetores. É rápido e não depende
# do download do `pt_core_news_sm` — este só é necessário para a lematização.
@lru_cache(maxsize=1)
def carregar_tokenizador_do_spacy():
    import spacy

    return spacy.blank("pt")


# Cache por texto: o experimento reprocessa o mesmo corpus milhares de vezes.
@lru_cache(maxsize=100_000)
def _tokenizar_com_spacy(texto: str) -> tuple[str, ...]:
    return tuple(token.text for token in carregar_tokenizador_do_spacy()(texto) if not token.is_space)


def tokenizar(texto: str, modo: Tokenizacao) -> list[str]:
    if modo is Tokenizacao.SPLIT:
        return texto.split()

    if modo is Tokenizacao.REGEX:
        from nltk.tokenize import wordpunct_tokenize

        return wordpunct_tokenize(texto)

    return list(_tokenizar_com_spacy(texto))


# -----------------------------------------------------------------------------
# Recursos linguísticos
# -----------------------------------------------------------------------------
# Os imports do NLTK e do spaCy ficam dentro das funções, e não no topo do
# arquivo, para que a mensagem de erro seja útil: quem esquecer de baixar os
# dados vê o comando que resolve, em vez de um LookupError cru do NLTK.


@lru_cache(maxsize=1)
def carregar_stopwords_do_nltk() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords

        return frozenset(stopwords.words("portuguese"))
    except LookupError as erro:
        raise RuntimeError(
            "Dados do NLTK não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from erro


# RSLP = Removedor de Sufixos da Língua Portuguesa (Orengo e Huyck, 2001), a
# implementação padrão do NLTK para o idioma. Oito passos de regras.
@lru_cache(maxsize=1)
def carregar_stemmer_rslp():
    try:
        from nltk.stem import RSLPStemmer

        return RSLPStemmer()
    except LookupError as erro:
        raise RuntimeError(
            "Dados do RSLP não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from erro


# A lematização do spaCy depende de classe gramatical: para saber que
# "vencendo" vem de "vencer", o modelo precisa antes reconhecer que é verbo.
# Por isso tagger e morphologizer ficam ligados. O parser sintático e o
# reconhecedor de entidades são desligados — não contribuem para o lema e
# respondem pela maior parte do tempo de processamento.
@lru_cache(maxsize=1)
def carregar_modelo_de_lematizacao_do_spacy():
    import spacy

    try:
        return spacy.load("pt_core_news_sm", disable=["parser", "ner"])
    except OSError as erro:
        raise RuntimeError(
            "Modelo de português do spaCy não encontrado. Rode uma vez:\n"
            "    python -m spacy download pt_core_news_sm"
        ) from erro


# -----------------------------------------------------------------------------
# Transformações
# -----------------------------------------------------------------------------


# NFKD separa "ç" em "c" + cedilha; o filtro joga fora tudo que for marca de
# combinação (categoria Unicode "Mn"), sobrando o caractere base.
def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


# Cache por palavra: o vocabulário é pequeno e os tokens se repetem muito, então
# o cache elimina quase todo o trabalho do RSLP nas milhares de reexecuções do
# experimento.
@lru_cache(maxsize=200_000)
def reduzir_palavra_ao_radical(palavra: str) -> str:
    return carregar_stemmer_rslp().stem(palavra)


# Diferente do stemming, a lematização NÃO pode ser feita palavra a palavra de
# forma isolada: o lema depende da classe gramatical, e a classe depende do
# contexto da frase. "Como" é verbo ou advérbio conforme o que está em volta.
# Por isso a unidade de cache aqui é o texto completo.
#
# Consequência a registrar: neste ponto quem tokeniza é o spaCy, porque a
# lematização é indissociável da análise que o modelo faz. A tokenização
# configurada volta a valer na materialização final.
@lru_cache(maxsize=100_000)
def lematizar(texto: str) -> str:
    modelo = carregar_modelo_de_lematizacao_do_spacy()
    return " ".join(token.lemma_ for token in modelo(texto) if not token.is_space)


# A lista do NLTK é um recurso lexical fixo: minúsculas, com acento, palavras
# inteiras. Se o texto já perdeu os acentos, ou já foi reduzido a radicais ou
# lemas, os tokens deixam de casar com a lista crua — a etapa rodaria sem erro
# nenhum e não removeria nada.
#
# Por isso a lista recebe as MESMAS transformações já aplicadas ao texto. E é
# por depender do que veio antes que esta etapa é sensível à ordem: com
# morfologia antes, a comparação passa a ser entre radicais (ou lemas), e o
# conjunto de palavras removidas muda de verdade.
#
# O que NÃO é compensado, de propósito: pontuação. Não há como acrescentar "o,"
# à lista. Se `stopwords` vier antes de `remover_pontuacao`, tokens grudados em
# vírgula escapam do filtro — e essa perda é um efeito real de ordem, que o
# experimento deve enxergar em vez de esconder.
@lru_cache(maxsize=256)
def montar_lista_de_stopwords_comparavel(
    modo: ModoStopwords, etapas_ja_aplicadas: tuple[str, ...], morfologia: ModoMorfologia
) -> frozenset[str]:
    palavras = set(carregar_stopwords_do_nltk())

    if modo is ModoStopwords.PRESERVAR_NEGACOES:
        palavras -= NEGACOES

    if "remover_acentos" in etapas_ja_aplicadas:
        palavras = {remover_acentos(p) for p in palavras}

    if "morfologia" in etapas_ja_aplicadas:
        if morfologia is ModoMorfologia.STEMMING:
            palavras = {reduzir_palavra_ao_radical(p) for p in palavras}
        elif morfologia is ModoMorfologia.LEMATIZACAO:
            palavras = {lematizar(p) for p in palavras}

    return frozenset(palavras)


# Aplica as etapas ligadas na ordem definida em `config.ordem` e devolve os
# tokens unidos por espaço — formato que o vetorizador consome com
# `tokenizer=str.split`, preservando exatamente a tokenização escolhida aqui.
#
# A ordem NÃO está embutida nesta função: ela percorre
# `config.etapas_ativas_na_ordem()`, que já vem ordenada, e vai registrando o
# que aplicou — informação de que a etapa de stopwords precisa para saber
# contra o que comparar.
#
# A tokenização configurada é usada TODA vez que o pipeline precisa de tokens:
# no filtro de stopwords, no stemming e na materialização final. É o que faz a
# escolha do tokenizador ser uma decisão de verdade, e não um detalhe do último
# passo.
#
# Com todas as etapas desligadas, devolve o texto original.
def preprocessar(texto: str, config: ConfigPreprocessamento) -> str:
    etapas_ja_aplicadas: list[str] = []

    for etapa in config.etapas_ativas_na_ordem():
        if etapa == "minusculas":
            texto = texto.lower()

        elif etapa == "remover_acentos":
            texto = remover_acentos(texto)

        elif etapa == "remover_pontuacao":
            texto = _PONTUACAO.sub(" ", texto)

        elif etapa == "remover_numeros":
            texto = _NUMEROS.sub(" ", texto)

        elif etapa == "stopwords":
            lista = montar_lista_de_stopwords_comparavel(
                config.stopwords, tuple(etapas_ja_aplicadas), config.morfologia
            )
            tokens = tokenizar(texto, config.tokenizacao)
            texto = " ".join(t for t in tokens if t.lower() not in lista)

        elif etapa == "morfologia":
            if config.morfologia is ModoMorfologia.STEMMING:
                tokens = tokenizar(texto, config.tokenizacao)
                texto = " ".join(reduzir_palavra_ao_radical(t) for t in tokens)
            elif config.morfologia is ModoMorfologia.LEMATIZACAO:
                texto = lematizar(texto)

        etapas_ja_aplicadas.append(etapa)

    # Normalizar espaço antes da materialização evita que espaços duplicados
    # deixados pelas substituições virem tokens vazios.
    texto_limpo = _ESPACOS_REPETIDOS.sub(" ", texto).strip()
    return " ".join(tokenizar(texto_limpo, config.tokenizacao))


# =============================================================================
# SEÇÃO 2 — VETORIZAÇÃO
# =============================================================================
# Segunda etapa do pipeline. O pré-processamento decide QUAIS tokens existem
# (SEÇÃO 1); a vetorização decide QUANTO cada token pesa e se sequências de
# tokens contam como unidade.
#
# É uma decisão independente da anterior, com seu próprio espaço de escolhas —
# e o experimento pode tratá-la em uma fase separada.
# =============================================================================


class ModoVetorizacao(StrEnum):
    # Como o peso de cada termo é calculado.
    #
    # BOW (bag of words): o peso é a contagem bruta do termo no documento.
    # Simples e literal. Trata "projeto", que aparece em quase toda frase, com
    # o mesmo prestígio de "desapropriação", que aparece em uma só.
    #
    # TFIDF: a contagem é multiplicada pelo IDF, fator que cresce quanto MAIS
    # RARO o termo é no corpus. Termo presente em todo documento não distingue
    # nada e é achatado; termo raro é destacado. É o conserto exato da fraqueza
    # do bag of words — mas em corpus pequeno o IDF fica instável, calculado
    # sobre poucas ocorrências, e nem sempre ganha.

    BOW = "bow"
    TFIDF = "tfidf"


# Janelas de n-grama testadas. `n_max=1` conta só palavras isoladas; `n_max=2`
# acrescenta os pares de palavras vizinhas.
#
# Bigrama existe para capturar o que a palavra sozinha perde: "não atualizou" e
# "atualizou" têm o mesmo unigrama "atualizou", mas bigramas diferentes. O
# custo é o vocabulário inflar muito — e vocabulário grande com poucos exemplos
# leva o modelo a decorar em vez de aprender.
JANELAS_NGRAMA: tuple[int, ...] = (1, 2)


@dataclass(frozen=True)
class ConfigVetorizacao:
    modo: ModoVetorizacao = ModoVetorizacao.TFIDF
    n_max: int = 1

    def descrever(self) -> str:
        janela = "1-2" if self.n_max >= 2 else "1"
        return f"{self.modo.value} n={janela}"


# A vetorização usada como RÉGUA quando o experimento roda em duas fases.
#
# Na primeira fase o objetivo é comparar pré-processamentos, então tudo o que
# vem depois precisa ficar constante — senão não há como saber se a diferença
# de resultado veio do texto ou da forma de contá-lo. TF-IDF com unigrama é a
# escolha convencional para esse papel: é o padrão da área e não favorece
# nenhuma estratégia de tokenização em particular.
VETORIZACAO_REFERENCIA = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)


# O espaço completo: 2 modos x 2 janelas = 4 opções.
def todas_as_vetorizacoes() -> list[ConfigVetorizacao]:
    return [ConfigVetorizacao(modo, n) for modo in ModoVetorizacao for n in JANELAS_NGRAMA]


# -----------------------------------------------------------------------------
# A ARMADILHA DOS PADRÕES DO SCIKIT-LEARN — leia antes de mexer aqui
# -----------------------------------------------------------------------------
# Por padrão, CountVectorizer e TfidfVectorizer fazem três coisas por conta
# própria: `lowercase=True` converte tudo para minúsculas, o `token_pattern`
# padrão (r"(?u)\b\w\w+\b") descarta pontuação e palavras de uma letra, e essa
# mesma expressão substitui qualquer tokenização feita antes.
#
# Com os padrões, três decisões do nosso experimento virariam enfeite:
# `minusculas` não teria efeito, `remover_pontuacao` também não, e as três
# estratégias de tokenização dariam resultados idênticos — porque o vetorizador
# retokenizaria tudo do seu jeito. O experimento reportaria "não faz diferença"
# para as três, medindo errado com toda a confiança.
#
# Por isso `lowercase=False` e `tokenizer=str.split`: o vetorizador apenas
# separa nos espaços que o pré-processamento já produziu e conta. Toda decisão
# de transformação e de tokenização fica na SEÇÃO 1, que é o objeto do estudo.
#
# Há testes em tests/test_vetorizacao.py que quebram se isto for revertido.
# -----------------------------------------------------------------------------
def construir_vetorizador(config: ConfigVetorizacao) -> CountVectorizer | TfidfVectorizer:
    classe = CountVectorizer if config.modo is ModoVetorizacao.BOW else TfidfVectorizer
    return classe(
        lowercase=False,      # quem decide é o preprocessar
        tokenizer=str.split,  # os tokens já vieram prontos, separados por espaço
        token_pattern=None,   # exigido pelo sklearn quando `tokenizer` é passado
        ngram_range=(1, config.n_max),
    )


# Vetorizador + Naive Bayes, usado pelo EXPERIMENTO como instrumento de medida.
#
# Não confundir com `construir_classificador` (SEÇÃO 3), que monta o modelo do
# produto. Aqui o classificador é a RÉGUA: para comparar formas de preparar o
# texto, tudo o que vem depois precisa ser idêntico — mesmo algoritmo, mesmos
# parâmetros, mesma semente. Naive Bayes serve bem porque é determinístico (sem
# sorteio interno nem otimização iterativa), rápido e funciona com poucos dados.
#
# E o Pipeline não é organização, é CORREÇÃO. Dentro da validação cruzada ele
# garante que o vocabulário e o IDF sejam aprendidos APENAS nas dobras de
# treino, e só então aplicados à dobra de teste. Aprender sobre o dataset
# inteiro seria vazamento de dados: a nota sobe, e sobe mentindo.
def construir_pipeline_de_medicao(config: ConfigVetorizacao) -> Pipeline:
    return Pipeline(
        [
            ("vetorizador", construir_vetorizador(config)),
            ("classificador", MultinomialNB(alpha=1.0)),
        ]
    )


# =============================================================================
# SEÇÃO 3 — CLASSIFICADOR (o modelo do produto)
# =============================================================================
# Os hiperparâmetros abaixo não foram escolhidos a dedo: saíram da busca em
# `ajuste_fino.py` (ver resultados/ajuste_fino.md).
#
# POR QUE NAIVE BAYES — E O QUE SE PERDEU NA TROCA
# ------------------------------------------------
# Esta parte usava regressão logística. A troca foi feita por medição, e o
# argumento que sustentava a escolha anterior continua parcialmente de pé; vale
# registrar os dois lados, porque quem mexer aqui depois precisa saber o que
# está sendo trocado por quê.
#
# A FAVOR:
#
# - Mede melhor neste dataset. Com os hiperparâmetros ajustados, 0,8725 de
#   F1-macro contra 0,8443 da regressão logística — mesmas dobras, mesma
#   semente. A diferença é menor que o desvio padrão entre dobras, então o
#   honesto é dizer "não perde", e não "ganha".
#
# - Aprende com pouquíssimo dado. Naive Bayes estima uma contagem por termo e
#   classe; não há otimização iterativa que precise de exemplos suficientes para
#   convergir. Com 120 frases, isso deixou de ser detalhe e virou o argumento
#   principal.
#
# - É determinístico. Sem sorteio interno, sem `random_state`, sem depender de
#   o otimizador ter convergido. Duas execuções dão exatamente o mesmo modelo.
#
# - A régua do experimento passa a ser da mesma família do modelo do produto.
#   A SEÇÃO 4 escolheu o pré-processamento medindo com `MultinomialNB`, e a
#   documentação registrava a ressalva de que a regressão logística poderia
#   preferir outro. Essa ressalva morre aqui. A contrapartida é que o
#   experimento deixa de ser um teste independente do produto — ele agora
#   confirma a si mesmo, e é por isso que `ajuste_fino.py` varre o
#   pré-processamento de novo em vez de aceitar o veredito da régua.
#
# CONTRA — o que se perdeu, e continua verdade:
#
# - A CALIBRAÇÃO DA CONFIANÇA PIOROU. Naive Bayes multiplica probabilidades
#   assumindo termos independentes; como não são, a evidência é contada mais de
#   uma vez e o resultado satura perto de 0 e 1. `prever_intencao` continua
#   devolvendo um número entre 0 e 1, mas ele ordena bem e calibra mal: serve
#   para comparar duas frases entre si, não para ser lido como "92% de chance de
#   estar certo". Um limiar de recusa fixado sobre este número vai recusar de
#   menos. Ver a ressalva em `prever_intencao`.
#
# - A suposição de independência continua falsa. Termos que sempre aparecem
#   juntos — "material rodante", "estrutura analítica" — são contados como duas
#   evidências separadas. É o preço do modelo, e não some com ajuste.
#
# O pipeline completo é um único objeto do scikit-learn:
#
#     texto bruto -> PreprocessadorDeTexto -> Vetorizador -> NaiveBayes
#
# Isso importa na prática: treinar, avaliar, salvar e prever passam a operar
# sobre TEXTO BRUTO. Não existe a possibilidade de alguém treinar com um
# pré-processamento e prever com outro — o erro mais comum e mais difícil de
# diagnosticar em PLN, porque não levanta exceção nenhuma: o modelo
# simplesmente erra mais.
# =============================================================================


class VarianteNB(StrEnum):
    # As três formas de Naive Bayes aplicáveis a texto. Diferem no que assumem
    # sobre a natureza do número que o vetorizador entrega.
    #
    # MULTINOMIAL: assume CONTAGEM. Modela cada classe como um sorteio de
    # palavras com reposição, então um termo que aparece três vezes pesa três
    # vezes mais. É o padrão da área para classificação de texto.
    #
    # COMPLEMENT: mesma mecânica, mas estima os pesos a partir do COMPLEMENTO da
    # classe — de tudo que NÃO é ela. Foi proposto (Rennie et al., 2003) para
    # corrigir o viés do multinomial em favor das classes maiores. Com classes
    # equilibradas a diferença é pequena; com dataset real desequilibrado, é a
    # variante que tende a segurar melhor a classe rara.
    #
    # BERNOULLI: assume PRESENÇA E AUSÊNCIA. Binariza a matriz — só importa se o
    # termo apareceu, não quantas vezes — e, diferente dos outros dois, usa a
    # AUSÊNCIA de um termo como evidência positiva para as classes em que ele
    # normalmente apareceria. Em frases curtas isso costuma vencer, e é o que
    # acontece aqui: nossas intenções são perguntas de uma linha, onde repetição
    # praticamente não ocorre e o que distingue é qual palavra está lá.

    MULTINOMIAL = "multinomial"
    COMPLEMENT = "complement"
    BERNOULLI = "bernoulli"


_CLASSES_NB = {
    VarianteNB.MULTINOMIAL: MultinomialNB,
    VarianteNB.COMPLEMENT: ComplementNB,
    VarianteNB.BERNOULLI: BernoulliNB,
}

# -----------------------------------------------------------------------------
# Os padrões, todos vindos de `ajuste_fino.py`
# -----------------------------------------------------------------------------
# ATENÇÃO — estes valores valem para o dataset de exemplo. Trocar o dataset os
# invalida, e o conserto é uma linha:
#
#     python -m az1.pln.ajuste_fino --dataset seus_dados.csv
#
# Não os edite a olho. Cada um é o vencedor de uma busca medida.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(remover_numeros=True, tokenizacao=Tokenizacao.REGEX)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
VARIANTE_PADRAO = VarianteNB.BERNOULLI
ALPHA_PADRAO = 0.1
FIT_PRIOR_PADRAO = True


# Adapta `preprocessar` à interface de transformador do scikit-learn.
#
# Com isto, o pré-processamento vira uma etapa do Pipeline em vez de um passo
# solto que alguém precisa lembrar de aplicar. O ganho é que o objeto salvo em
# disco carrega a própria configuração: quem carregar o modelo depois não tem
# como aplicar outra por engano.
#
# DETALHE DA CONSOLIDAÇÃO: o joblib grava no arquivo o CAMINHO DO MÓDULO desta
# classe. Um modelo salvo por aqui guarda `az1.pln.pln_completo`; um salvo por
# `classificador.py` guarda `az1.pln.classificador`. Carregar exige que o
# módulo correspondente seja importável — por isso os dois arquivos gravam em
# caminhos diferentes por padrão, e um não lê o do outro por acidente.
class PreprocessadorDeTexto(BaseEstimator, TransformerMixin):
    # A configuração fica em `self.config` sem nenhuma alteração, e não em um
    # atributo derivado. É exigência do `clone()`, que a validação cruzada usa
    # para criar uma cópia limpa a cada dobra: ele reconstrói o objeto a partir
    # dos parâmetros do `__init__`, e qualquer processamento feito ali se perde.
    def __init__(self, config: ConfigPreprocessamento = CONFIG_PRE_PADRAO) -> None:
        self.config = config

    # Não faz nada porque o pré-processamento não aprende nada dos dados — é
    # uma transformação determinística. Ainda assim precisa existir e devolver
    # `self`, que é o contrato do scikit-learn.
    def fit(self, X, y=None):  # noqa: N803 — nomes exigidos pela interface do sklearn
        return self

    def transform(self, X):  # noqa: N803
        return [preprocessar(texto, self.config) for texto in X]


# Monta o pipeline completo: texto bruto -> intenção.
#
# Sobre os parâmetros do Naive Bayes:
#
# - `alpha` é a suavização de Laplace/Lidstone: a contagem fictícia somada a
#   TODO par (termo, classe) antes de virar probabilidade. Sem ela, um termo
#   que nunca apareceu numa classe teria probabilidade zero, e um único zero
#   zera o produto inteiro — uma palavra desconhecida bastaria para eliminar
#   uma intenção, por mais que todo o resto da frase apontasse para ela.
#
#   O valor controla o quanto o modelo confia nas contagens observadas. ALTO
#   puxa tudo para a distribuição uniforme e apaga as diferenças entre classes;
#   BAIXO confia em contagens vistas duas ou três vezes e decora. Com 120
#   frases o ótimo medido ficou em 0,1 — abaixo do padrão 1,0 do scikit-learn,
#   o que é coerente: vocabulário pequeno e frases curtas produzem contagens
#   baixas, que a suavização padrão abafaria.
#
#   É o `alpha` que faz aqui o papel que `C` fazia na regressão logística, com
#   o sentido INVERTIDO: `C` alto = menos regularização, `alpha` alto = mais.
#
# - `fit_prior` decide se as probabilidades a priori das classes são aprendidas
#   da frequência no treino (`True`) ou fixadas em uniformes (`False`).
#   `False` é o análogo mais próximo do `class_weight="balanced"` que a
#   regressão logística usava — Naive Bayes não tem `class_weight`. Fica em
#   `True` porque foi o que mediu melhor e porque as três classes do dataset de
#   exemplo têm o mesmo tamanho, o que torna a escolha quase inócua aqui.
#   Em dataset real desequilibrado, vale medir os dois de novo.
#
# - Não há `random_state`. Naive Bayes é determinístico: nada a semear.
def construir_classificador(
    config_pre: ConfigPreprocessamento = CONFIG_PRE_PADRAO,
    config_vet: ConfigVetorizacao = CONFIG_VET_PADRAO,
    variante: VarianteNB = VARIANTE_PADRAO,
    alpha: float = ALPHA_PADRAO,
    fit_prior: bool = FIT_PRIOR_PADRAO,
) -> Pipeline:
    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", _CLASSES_NB[variante](alpha=alpha, fit_prior=fit_prior)),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia por validação cruzada e devolve (F1-macro, relatório, matriz, classes).
#
# RENOMEADA NA CONSOLIDAÇÃO — era `avaliar_com_validacao_cruzada` em
# classificador.py. O experimento tinha uma função de mesmo nome e assinatura
# diferente, que aqui virou `medir_configuracao` (SEÇÃO 4). Esta avalia um
# MODELO PRONTO; aquela mede UMA CONFIGURAÇÃO.
#
# Usa `cross_val_predict`, que devolve, para cada exemplo, a previsão feita
# quando ele estava FORA do treino. Isso permite montar um relatório por classe
# e uma matriz de confusão sobre o dataset inteiro, sem que nenhuma previsão
# tenha visto o próprio exemplo durante o treino.
#
# Por que não avaliar sobre o treino: o modelo acerta quase tudo no que já viu.
# A nota de treino mede memória, não capacidade de generalizar.
def avaliar_classificador(
    textos: list[str], rotulos: list[str], modelo: Pipeline, k: int = 5
) -> tuple[float, str, list[list[int]], list[str]]:
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    preditos = cross_val_predict(modelo, textos, rotulos, cv=dobras)

    classes = sorted(set(rotulos))
    return (
        f1_score(rotulos, preditos, average="macro"),
        classification_report(rotulos, preditos, digits=3, zero_division=0),
        confusion_matrix(rotulos, preditos, labels=classes).tolist(),
        classes,
    )


# As palavras que mais distinguem cada intenção. Exige o modelo já treinado.
#
# COMO SE LÊ UM NAIVE BAYES — e por que não basta olhar `feature_log_prob_`
# -------------------------------------------------------------------------
# A regressão logística tinha `coef_`: um peso por termo e classe, já
# centrado, em que positivo significa "empurra para esta classe". Naive Bayes
# não tem isso — e, desde o scikit-learn 1.2, também não tem mais o `coef_` de
# compatibilidade que existiu até a 1.0. O que existe é `feature_log_prob_`,
# que é log P(termo | classe): quão PROVÁVEL o termo é dentro da classe.
#
# Ordenar por esse número cru dá a lista errada. Ele é dominado pelos termos
# mais frequentes do corpus — "de", "do", "projeto" —, que são prováveis em
# TODAS as classes e por isso não distinguem nenhuma. O topo sairia idêntico
# para as três intenções.
#
# O que distingue é o CONTRASTE: o quanto o termo é mais provável nesta classe
# do que nas demais. É a razão de chances em log,
#
#     log P(termo | classe)  -  média de log P(termo | outras classes)
#
# que zera para termos indiferentes e cresce só para os característicos. Isso
# recupera exatamente a leitura que `coef_` dava, e por isso a função mantém o
# nome e o contrato: (termo, peso), do mais característico ao menos.
#
# Sobre as três variantes: `feature_log_prob_` do ComplementNB é estimado sobre
# o complemento da classe, mas o scikit-learn já o armazena NEGADO (`norm=False`,
# o padrão), de modo que "maior = mais indicativo desta classe" vale para as
# três. Se alguém ligar `norm=True`, esse sinal se inverte e esta função passa a
# listar o oposto do pretendido.
#
# Auditar esta lista costuma revelar problemas do dataset antes de qualquer
# métrica: se uma intenção estiver sendo decidida por uma palavra que só
# aparece por acaso nos exemplos daquela classe, aparece aqui.
def listar_palavras_de_maior_peso_por_intencao(
    modelo: Pipeline, quantas: int = 8
) -> dict[str, list[tuple[str, float]]]:
    vetorizador = modelo.named_steps["vetorizador"]
    classificador = modelo.named_steps["classificador"]
    termos = vetorizador.get_feature_names_out()
    log_prob = classificador.feature_log_prob_

    por_classe: dict[str, list[tuple[str, float]]] = {}
    for indice, classe in enumerate(classificador.classes_):
        outras = np.delete(log_prob, indice, axis=0)
        # Com uma classe só não há contraste possível; o peso vira o log-prob cru.
        contraste = log_prob[indice] - (outras.mean(axis=0) if outras.size else 0.0)
        ordenados = sorted(
            zip(termos, contraste.tolist(), strict=True), key=lambda par: par[1], reverse=True
        )
        por_classe[str(classe)] = ordenados[:quantas]
    return por_classe


# Devolve (intenção, confiança) para um texto.
#
# RESSALVA IMPORTANTE — A CONFIANÇA DO NAIVE BAYES É MAL CALIBRADA
# -----------------------------------------------------------------
# O número devolvido é `predict_proba` da classe escolhida, entre 0 e 1, e as
# três somam 1. Mas ele NÃO deve ser lido como "chance de estar certo".
#
# Naive Bayes multiplica a probabilidade de cada termo assumindo que são
# independentes. Não são: "prazo" e "vencer" aparecem juntos o tempo todo, e
# cada par correlacionado é contado como se fosse evidência nova. Multiplicar
# dezenas dessas evidências infladas empurra o resultado para os extremos, e a
# saída satura em 0,99 mesmo quando o modelo está em dúvida. A regressão
# logística que este pipeline usava antes calibrava melhor; foi o que se perdeu
# na troca.
#
# O que o número AINDA serve para fazer: ORDENAR. Entre duas frases, a de maior
# confiança é de fato aquela sobre a qual o modelo tem mais evidência. Então um
# limiar de recusa continua utilizável — mas o valor do limiar tem de ser
# calibrado empiricamente sobre dados rotulados, e não escolhido por intuição.
# Um "0,7" pensado para regressão logística aqui não recusa quase nada.
#
# RESSALVA SEPARADA — a confiança não resolve o caso fora do catálogo. Um modelo
# que conhece três classes é obrigado a escolher uma delas, e pode fazê-lo com
# convicção alta para uma pergunta sem relação nenhuma com o portfólio. Só o
# dataset resolve isso, com exemplos rotulados da categoria fora do catálogo.
def prever_intencao(modelo: Pipeline, texto: str) -> tuple[str, float]:
    probabilidades = modelo.predict_proba([texto])[0]
    indice = probabilidades.argmax()
    return str(modelo.named_steps["classificador"].classes_[indice]), float(probabilidades[indice])


def salvar_modelo(modelo: Pipeline, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path) -> Pipeline:
    return joblib.load(caminho)


def imprimir_matriz_de_confusao(matriz: list[list[int]], classes: list[str]) -> None:
    largura = max(len(c) for c in classes) + 2
    print("Matriz de confusão — linha = intenção real, coluna = prevista")
    print(" " * largura + "".join(f"{c:>{largura}}" for c in classes))
    for classe, linha in zip(classes, matriz, strict=True):
        print(f"{classe:>{largura}}" + "".join(f"{v:>{largura}}" for v in linha))


# =============================================================================
# SEÇÃO 4 — EXPERIMENTO (a busca pela melhor configuração)
# =============================================================================
# O que esta seção responde, com número em vez de opinião:
#
# 1. Quais etapas de pré-processamento ajudam neste dataset?
# 2. A ORDEM das etapas importa? A ordem padrão é a melhor?
# 3. Remover stopwords ajuda? E remover preservando as negações?
# 4. Stemming ou lematização — qual reduz melhor as palavras?
# 5. Qual estratégia de tokenização produz o melhor vocabulário?
# 6. Qual vetorização e qual janela de n-grama?
#
# MÉTODO PADRÃO: VARREDURA EXAUSTIVA
# ----------------------------------
# Por padrão o experimento testa o produto cartesiano completo — cada
# pré-processamento contra cada vetorização. É o único método que encontra o
# ótimo global, e no nosso tamanho de dataset custa alguns minutos.
#
# A alternativa `--duas-fases` faz uma busca em estágios:
#
#     FASE 1  varre o pré-processamento com a vetorização FIXA
#                           |
#                           v
#             seleciona as melhores configurações
#                           |
#                           v
#     FASE 2  varre a vetorização sobre essas configurações
#
# Custa 1/4 das avaliações. POR QUE NÃO É O PADRÃO — busca em estágios não
# garante o ótimo global, e neste dataset comprovadamente não o encontra. O
# melhor pré-processamento sob TF-IDF não é o melhor sob bag-of-words:
# `remover_numeros` é medíocre sob a régua TF-IDF (79º lugar na Fase 1) e é a
# melhor configuração sob bag-of-words. A busca em estágios perde essa
# combinação por 0,0078 de F1.
#
# O modo em duas fases continua útil quando a varredura completa ficar cara —
# dataset grande, muitas dobras, espaço de busca ampliado. Nesses casos,
# `--top-fase1` alto reduz a chance de perder o ótimo.
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
# =============================================================================

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


# Validação cruzada estratificada. Devolve (F1 médio, desvio, vocabulário médio).
#
# RENOMEADA NA CONSOLIDAÇÃO — era `avaliar_com_validacao_cruzada` em
# experimento.py, nome que o classificador também usava para outra coisa. Esta
# mede UMA CONFIGURAÇÃO sobre um corpus JÁ pré-processado; a da SEÇÃO 3,
# `avaliar_classificador`, avalia um modelo pronto sobre texto bruto.
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
    vocabularios = [len(e.named_steps["vetorizador"].vocabulary_) for e in saida["estimator"]]
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
# Por padrão `vetorizacoes` traz as quatro, e o resultado é o produto
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
                media, desvio, vocabulario = medir_configuracao(corpus, rotulos, vetorizacao, k)
                resultados.append(
                    Resultado(config, vetorizacao, media, desvio, vocabulario, equivalentes, tem_a_padrao)
                )

        if sys.stdout.isatty():
            print(f"\r  {numero}/{len(configuracoes)} configurações de pré-processamento", end="", flush=True)

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados, permutacoes_examinadas


# As configurações que passam para a Fase 2.
#
# São as `quantas` melhores por F1, mais duas de controle que entram sempre,
# ainda que não estejam no topo:
#
# - a MAIS SIMPLES entre as empatadas com a primeira (dentro de um desvio
#   padrão). Se ela vencer na Fase 2 também, adotamos menos etapas pelo mesmo
#   resultado;
# - o TEXTO CRU, como linha de base. Sem ele não há como afirmar que o
#   pré-processamento agregou alguma coisa.
#
# Configurações repetidas são descartadas — a mesma configuração pode aparecer
# mais de uma vez no ranking sob ordens diferentes que produziram textos
# diferentes.
def selecionar_melhores_para_a_fase2(
    resultados: list[Resultado], quantas: int
) -> list[ConfigPreprocessamento]:
    escolhidas: list[ConfigPreprocessamento] = []
    ja_vistas: set[ConfigPreprocessamento] = set()

    def acrescentar(config: ConfigPreprocessamento) -> None:
        if config not in ja_vistas:
            ja_vistas.add(config)
            escolhidas.append(config)

    for resultado in resultados[:quantas]:
        acrescentar(resultado.config)

    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatadas = [r for r in resultados if r.f1_medio >= limiar]
    if empatadas:
        mais_simples = min(
            empatadas, key=lambda r: (len(r.config.etapas_ativas_na_ordem()), -r.f1_medio)
        )
        acrescentar(mais_simples.config)

    acrescentar(ConfigPreprocessamento())
    return escolhidas


# Testa todas as vetorizações sobre cada configuração selecionada.
#
# Aqui o texto é a constante e a vetorização é a variável — o inverso exato da
# Fase 1. Como as configurações vieram prontas, o corpus é recalculado uma vez
# por configuração e reaproveitado nas quatro vetorizações.
def varrer_vetorizacoes_das_selecionadas(
    textos: list[str],
    rotulos: list[str],
    selecionadas: list[ConfigPreprocessamento],
    k: int,
) -> list[Resultado]:
    resultados: list[Resultado] = []
    vetorizacoes = todas_as_vetorizacoes()

    for numero, config in enumerate(selecionadas, start=1):
        corpus = [preprocessar(texto, config) for texto in textos]
        for vetorizacao in vetorizacoes:
            media, desvio, vocabulario = medir_configuracao(corpus, rotulos, vetorizacao, k)
            resultados.append(Resultado(config, vetorizacao, media, desvio, vocabulario))

        if sys.stdout.isatty():
            print(f"\r  Fase 2: {numero}/{len(selecionadas)} configurações", end="", flush=True)

    if sys.stdout.isatty():
        print()

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados


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


# Efeito de cada escolha de vetorização, PAREADO por pré-processamento.
#
# Cada configuração selecionada foi avaliada sob as quatro vetorizações, e são
# exatamente esses quartetos que se comparam entre si. Como o texto é idêntico
# dentro de cada quarteto, a diferença só pode vir da vetorização.
def medir_efeito_da_vetorizacao(
    resultados: list[Resultado],
) -> list[tuple[str, float, float, int]]:
    por_configuracao: dict[ConfigPreprocessamento, dict[ConfigVetorizacao, float]] = defaultdict(dict)
    for resultado in resultados:
        por_configuracao[resultado.config][resultado.vetorizacao] = resultado.f1_medio

    completos = [g for g in por_configuracao.values() if len(g) == 4]
    if not completos:
        return []

    linhas: list[tuple[str, float, float, int]] = []
    for nome, pertence_ao_grupo in (
        ("tfidf (vs bow)", lambda v: v.modo is ModoVetorizacao.TFIDF),
        ("bigrama (vs só uni)", lambda v: v.n_max >= 2),
    ):
        com = [statistics.mean(f for v, f in g.items() if pertence_ao_grupo(v)) for g in completos]
        sem = [statistics.mean(f for v, f in g.items() if not pertence_ao_grupo(v)) for g in completos]
        linhas.append((nome, statistics.mean(com), statistics.mean(sem), len(completos)))

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

    # No modo exaustivo cada corpus foi avaliado sob as 4 vetorizações, então o
    # efeito delas é mensurável aqui. No modo duas fases isso não vale — a Fase
    # 1 roda com uma vetorização só — e a tabela sai em `imprimir_fase2`.
    if not duas_fases:
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


def imprimir_fase2(
    resultados: list[Resultado], selecionadas: list[ConfigPreprocessamento], top: int
) -> None:
    print(f"\n{'=' * LARGURA}")
    print(f"{'FASE 2 — VETORIZAÇÃO (sobre os melhores pré-processamentos)':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"  Configurações herdadas da Fase 1 : {len(selecionadas)}")
    print(f"  Vetorizações testadas em cada uma: {len(todas_as_vetorizacoes())}")
    print(f"  Execuções desta fase             : {len(resultados)}\n")
    imprimir_ranking(resultados, top)

    linhas = medir_efeito_da_vetorizacao(resultados)
    if linhas:
        cabecalho = f"EFEITO DA VETORIZAÇÃO — pareado em {linhas[0][3]} pré-processamentos"
        print(f"\n{cabecalho:^{LARGURA}}")
        print(f"{'escolha':>24}  {'com':>8}  {'sem':>10}  {'efeito':>9}")
        print("-" * LARGURA)
        for nome, com, sem, _ in linhas:
            efeito = com - sem
            marca = "  <- atrapalha" if efeito < -0.01 else ("  <- ajuda" if efeito > 0.01 else "")
            print(f"{nome:>24}  {com:>8.4f}  {sem:>10.4f}  {efeito:>+9.4f}{marca}")


# Regra da parcimônia: entre configurações estatisticamente empatadas com a
# melhor, prefira a mais simples. Uma etapa a mais que não paga o próprio custo
# é complexidade sem retorno — e mais uma coisa para dar errado.
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
    resultados_principais: list[Resultado],
    resultados_fase2: list[Resultado],
    selecionadas: list[ConfigPreprocessamento],
    dataset: Path,
    k: int,
    permutacoes: int,
    variar_ordem: bool,
    duas_fases: bool,
) -> None:
    RESULTADOS_DIR.mkdir(exist_ok=True)

    with RELATORIO_CSV.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(
            ["fase", "posicao", "f1_macro_medio", "desvio_padrao", "vocabulario_medio", "vetorizador",
             "n_max", "ordem", "ordens_equivalentes", "e_a_ordem_padrao", "minusculas", "remover_acentos",
             "remover_pontuacao", "remover_numeros", "stopwords", "morfologia", "tokenizacao"]
        )
        for fase, conjunto in (("1", resultados_principais), ("2", resultados_fase2)):
            for posicao, r in enumerate(conjunto, start=1):
                c = r.config
                escritor.writerow(
                    [fase, posicao, f"{r.f1_medio:.6f}", f"{r.f1_desvio:.6f}",
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
        "- Gerado por `pln_completo.py` (versão consolidada em arquivo único)",
        "",
        ("## Fase 1 — pré-processamento" if duas_fases
         else "## Varredura exaustiva — pré-processamento x vetorização"),
        "",
        (f"Vetorização fixa como régua: `{VETORIZACAO_REFERENCIA.descrever()}`." if duas_fases
         else "Produto cartesiano completo: cada pré-processamento contra as "
              f"{len(todas_as_vetorizacoes())} vetorizações."),
        f"Permutações de ordem examinadas: {permutacoes}. Execuções distintas: {len(resultados_principais)}.",
        "",
        "### Efeito de cada etapa booleana",
        "",
        "| etapa | com | sem | efeito |",
        "|---|---|---|---|",
    ]
    for nome, com, sem, efeito in medir_efeito_das_etapas_booleanas(resultados_principais):
        linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {efeito:+.4f} |")

    for campo, enum_do_campo in CAMPOS_CATEGORICOS:
        linhas_campo, pareamentos = comparar_valores_pareados(resultados_principais, campo, enum_do_campo)
        referencia = list(enum_do_campo)[0].value
        linhas += [
            "", f"### {campo.capitalize()}", "",
            f"Comparação **pareada** em {pareamentos} configurações idênticas nas demais escolhas.",
            "", f"| opção | F1 médio | vs {referencia} |", "|---|---|---|",
        ]
        for valor, media, diferenca in linhas_campo:
            linhas.append(f"| {valor} | {media:.4f} | {diferenca:+.4f} |")

    if variar_ordem:
        analise = analisar_efeito_da_ordem(resultados_principais)
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

    if not resultados_fase2:
        linhas_vetorizacao = medir_efeito_da_vetorizacao(resultados_principais)
        if linhas_vetorizacao:
            linhas += [
                "", "### Efeito da vetorização", "",
                f"Comparação **pareada** em {linhas_vetorizacao[0][3]} pré-processamentos: cada um foi",
                "avaliado sob as quatro vetorizações, e é esse quarteto que se compara entre si.",
                "", "| escolha | com | sem | efeito |", "|---|---|---|---|",
            ]
            for nome, com, sem, _ in linhas_vetorizacao:
                linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {com - sem:+.4f} |")

        linhas += ["", "### Ranking (top 30)", "",
                   "| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |", "|---|---|---|---|---|---|"]
        for posicao, r in enumerate(resultados_principais[:30], start=1):
            linhas.append(
                f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | {r.tamanho_vocabulario:.0f} "
                f"| {r.vetorizacao.descrever()} | {r.config.descrever()} |"
            )
    else:
        linhas += [
            "", "## Fase 2 — vetorização", "",
            f"{len(selecionadas)} configurações herdadas da Fase 1, cada uma sob "
            f"{len(todas_as_vetorizacoes())} vetorizações.",
            "", "| escolha | com | sem | efeito |", "|---|---|---|---|",
        ]
        for nome, com, sem, _ in medir_efeito_da_vetorizacao(resultados_fase2):
            linhas.append(f"| {nome} | {com:.4f} | {sem:.4f} | {com - sem:+.4f} |")

        linhas += ["", "### Ranking final", "",
                   "| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |", "|---|---|---|---|---|---|"]
        for posicao, r in enumerate(resultados_fase2[:30], start=1):
            linhas.append(
                f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | {r.tamanho_vocabulario:.0f} "
                f"| {r.vetorizacao.descrever()} | {r.config.descrever()} |"
            )

    RELATORIO_MD.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em:\n  {RELATORIO_CSV}\n  {RELATORIO_MD}")


# =============================================================================
# SEÇÃO 5 — LINHA DE COMANDO
# =============================================================================
# Os módulos originais tinham um `main()` cada: um treinava o classificador, o
# outro rodava o experimento. Juntar os arquivos faria o segundo `def main`
# apagar o primeiro em silêncio, então aqui existe UM ponto de entrada com
# subcomandos, e cada `main` antigo virou uma função `comando_*`.
#
#     treinar      python -m az1.pln.pln_completo treinar
#     prever       python -m az1.pln.pln_completo prever "Quais prazos vencem?"
#     experimento  python -m az1.pln.pln_completo experimento --sem-ordem
#
# Equivalências com os módulos originais:
#
#     python -m az1.pln.classificador            -> ... pln_completo treinar
#     python -m az1.pln.classificador --prever X -> ... pln_completo prever X
#     python -m az1.pln.experimento              -> ... pln_completo experimento
# =============================================================================


def comando_treinar(args: argparse.Namespace) -> int:
    fit_prior = not args.sem_priori
    textos, rotulos = carregar_dataset(args.dataset)

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Pré-processamento: {CONFIG_PRE_PADRAO.descrever()}")
    print(f"Vetorização      : {CONFIG_VET_PADRAO.descrever()}")
    print(f"Classificador    : {_CLASSES_NB[args.variante].__name__}"
          f"(alpha={args.alpha}, fit_prior={fit_prior})\n")

    modelo = construir_classificador(variante=args.variante, alpha=args.alpha, fit_prior=fit_prior)
    f1, relatorio, matriz, classes = avaliar_classificador(textos, rotulos, modelo, args.k)

    print(f"F1-macro (validação cruzada de {args.k} dobras): {f1:.4f}\n")
    print(relatorio)
    imprimir_matriz_de_confusao(matriz, classes)

    # Treina no dataset completo para salvar. A avaliação acima já foi feita
    # sem que nenhuma previsão visse o próprio exemplo; aqui o objetivo é
    # aproveitar todos os dados disponíveis no modelo que vai a disco.
    modelo.fit(textos, rotulos)
    print("\nPalavras que mais distinguem cada intenção")
    for classe, termos in listar_palavras_de_maior_peso_por_intencao(modelo).items():
        print(f"  {classe:>10}: " + ", ".join(termo for termo, _ in termos))

    salvar_modelo(modelo, args.salvar)
    print(f"\nModelo treinado no dataset completo e salvo em {args.salvar}")
    print('Teste: python -m az1.pln.pln_completo prever "Quais prazos vencem esta semana?"')
    return 0


def comando_prever(args: argparse.Namespace) -> int:
    if not args.modelo.exists():
        print(f"❌ Modelo não encontrado em {args.modelo}. Treine primeiro:\n"
              f"    python -m az1.pln.pln_completo treinar")
        return 1

    intencao, confianca = prever_intencao(carregar_modelo(args.modelo), args.frase)
    print(f"{args.frase!r}\n  -> {intencao}  (confiança {confianca:.1%})")
    return 0


def comando_experimento(args: argparse.Namespace) -> int:
    textos, rotulos = carregar_dataset(args.dataset)

    variar_ordem = not args.sem_ordem
    vetorizacoes = [VETORIZACAO_REFERENCIA] if args.duas_fases else todas_as_vetorizacoes()

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Distribuição: {dict(Counter(rotulos))}")
    print(f"Configurações de pré-processamento: {len(todas_as_configuracoes_de_preprocessamento())}")
    print(f"Varredura de ordem: "
          f"{'todas as permutações das etapas ativas' if variar_ordem else 'somente a ordem padrão'}")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}")
    if args.duas_fases:
        print(f"Busca em DUAS FASES. Fase 1 com vetorização fixa: {VETORIZACAO_REFERENCIA.descrever()}")
        print("  (4x mais rápida que a varredura exaustiva, mas pode perder o ótimo global)\n")
    else:
        print(f"Varredura EXAUSTIVA: cada pré-processamento contra as {len(vetorizacoes)} vetorizações\n")

    principais, permutacoes = varrer_espaco_de_busca(textos, rotulos, args.k, variar_ordem, vetorizacoes)
    imprimir_varredura(principais, args.top, permutacoes, variar_ordem, args.duas_fases)

    resultados_fase2: list[Resultado] = []
    selecionadas: list[ConfigPreprocessamento] = []
    if args.duas_fases:
        selecionadas = selecionar_melhores_para_a_fase2(principais, args.top_fase1)
        resultados_fase2 = varrer_vetorizacoes_das_selecionadas(textos, rotulos, selecionadas, args.k)
        imprimir_fase2(resultados_fase2, selecionadas, args.top)

    imprimir_recomendacao(resultados_fase2 or principais)
    escrever_relatorio(
        principais, resultados_fase2, selecionadas, args.dataset, args.k,
        permutacoes, variar_ordem, args.duas_fases,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pln_completo",
        description="Pipeline de PLN completo: pré-processamento, vetorização, classificação e experimento.",
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    treinar = subcomandos.add_parser("treinar", help="treina, avalia por validação cruzada e salva o modelo")
    treinar.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    treinar.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    treinar.add_argument("--variante", type=VarianteNB, choices=list(VarianteNB),
                         default=VARIANTE_PADRAO, help="variante de Naive Bayes")
    treinar.add_argument("--alpha", type=float, default=ALPHA_PADRAO,
                         help="suavização de Laplace/Lidstone")
    treinar.add_argument("--sem-priori", action="store_true",
                         help="usa probabilidades a priori uniformes em vez das do treino")
    treinar.add_argument("--salvar", type=Path, default=MODELO_PADRAO, help="onde gravar o modelo")
    treinar.set_defaults(funcao=comando_treinar)

    prever = subcomandos.add_parser("prever", help="classifica uma frase com o modelo salvo")
    prever.add_argument("frase", type=str, help="a frase a classificar")
    prever.add_argument("--modelo", type=Path, default=MODELO_PADRAO, help="modelo a carregar")
    prever.set_defaults(funcao=comando_prever)

    experimento = subcomandos.add_parser(
        "experimento", help="busca a melhor configuração de pré-processamento e vetorização"
    )
    experimento.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    experimento.add_argument("--k", type=int, default=5, help="número de dobras da validação cruzada")
    experimento.add_argument("--top", type=int, default=10, help="quantas linhas mostrar em cada ranking")
    experimento.add_argument("--sem-ordem", action="store_true",
                             help="usa só a ordem padrão (execução rápida)")
    experimento.add_argument("--duas-fases", action="store_true",
                             help="busca em estágios em vez da varredura exaustiva: 4x mais rápida, "
                                  "mas pode perder o ótimo global")
    experimento.add_argument("--top-fase1", type=int, default=20,
                             help="com --duas-fases: quantas configurações passam para a Fase 2")
    experimento.set_defaults(funcao=comando_experimento)

    args = parser.parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    raise SystemExit(main())
