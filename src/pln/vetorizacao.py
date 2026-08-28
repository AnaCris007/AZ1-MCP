# =============================================================================
# vetorizacao.py — Conversão de tokens em matriz numérica
# =============================================================================
# Segunda etapa do pipeline. O pré-processamento decide QUAIS tokens existem
# (ver preprocessamento.py); a vetorização decide COMO cada token vira número.
#
# Há duas famílias aqui, e elas são diferentes em espécie, não em grau:
#
#   ESPARSAS (bag of words, TF-IDF) — uma coluna por termo do corpus, quase
#   tudo zero. O número diz "quantas vezes este termo apareceu". Não sabem nada
#   sobre a língua: para elas, "prazo" e "cronograma" são colunas tão distintas
#   quanto "prazo" e "banana".
#
#   DENSAS (embeddings pré-treinados) — 300 colunas fixas, todas preenchidas,
#   vindas de um modelo treinado em bilhões de palavras. O número não diz nada
#   isoladamente; o que significa algo é a POSIÇÃO do documento no espaço. Aí
#   "prazo" e "cronograma" ficam perto, e é essa a aposta.
#
# A diferença tem uma consequência que atravessa o arquivo inteiro: vetores
# densos têm valores NEGATIVOS, e Multinomial/Complement Naive Bayes exigem
# entrada não-negativa. Ver `construir_pipeline_de_medicao`.
#
# Dependência de dados para os embeddings, baixada uma vez:
#     python -m spacy download pt_core_news_md
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.pipeline import Pipeline

# O modelo de onde saem os vetores pré-treinados.
#
# ATENÇÃO AO QUE ELE É, DE FATO: os vetores do `pt_core_news_md` são fastText
# treinado com CBOW sobre OSCAR Common Crawl + Wikipédia — está na própria
# metadata do modelo (`nlp.meta["sources"]`). NÃO são Word2Vec skip-gram.
#
# CBOW e skip-gram são os dois objetivos de treino do Word2Vec e são inversos:
# CBOW prevê a palavra a partir do contexto, skip-gram prevê o contexto a partir
# da palavra. Skip-gram costuma representar melhor palavra rara — que é
# exatamente o caso de "desapropriação" ou "material rodante" no nosso domínio.
# fastText acrescenta uma terceira coisa: compõe o vetor a partir de pedaços da
# palavra, o que lhe dá vetor para palavra nunca vista.
#
# Para usar skip-gram de verdade seria preciso um arquivo de vetores treinado
# assim — os do NILC/USP são a referência em português — e trocar a constante
# abaixo por um carregador daquele formato. Enquanto isso não existe, o nome do
# modo é `EMBEDDING`, e não `W2V_SKIPGRAM`, porque nomear errado é a forma mais
# barata de mentir num relatório.
MODELO_DE_VETORES = "pt_core_news_md"


class ModoVetorizacao(StrEnum):
    # BOW (bag of words): o peso é a contagem bruta do termo no documento.
    # Simples e literal. Trata "projeto", que aparece em quase toda frase, com
    # o mesmo prestígio de "desapropriação", que aparece em uma só.
    #
    # TFIDF: a contagem é multiplicada pelo IDF, fator que cresce quanto MAIS
    # RARO o termo é no corpus. Termo presente em todo documento não distingue
    # nada e é achatado; termo raro é destacado. É o conserto exato da fraqueza
    # do bag of words — mas em corpus pequeno o IDF fica instável, calculado
    # sobre poucas ocorrências, e nem sempre ganha.
    #
    # EMBEDDING: o documento vira a MÉDIA dos vetores pré-treinados dos seus
    # tokens. Traz conhecimento de fora do nosso corpus — sabe que "prazo" e
    # "cronograma" são parentes sem nunca ter visto nossas 300 frases. O preço é
    # que a média destrói a ordem e dilui: uma frase longa vira um ponto no meio
    # de tudo que ela contém, e a negação some por completo — "não venceu" e
    # "venceu" ficam quase no mesmo lugar.

    BOW = "bow"
    TFIDF = "tfidf"
    EMBEDDING = "embedding"


# Janelas de n-grama testadas. `n_max=1` conta só palavras isoladas; `n_max=2`
# acrescenta os pares de palavras vizinhas.
#
# Bigrama existe para capturar o que a palavra sozinha perde: "não atualizou" e
# "atualizou" têm o mesmo unigrama "atualizou", mas bigramas diferentes. O
# custo é o vocabulário inflar muito — e vocabulário grande com poucos exemplos
# leva o modelo a decorar em vez de aprender.
#
# Só se aplica às vetorizações esparsas: a média de embeddings não tem coluna
# por termo onde um bigrama pudesse entrar.
JANELAS_NGRAMA: tuple[int, ...] = (1, 2)


@dataclass(frozen=True)
class ConfigVetorizacao:
    modo: ModoVetorizacao = ModoVetorizacao.TFIDF
    n_max: int = 1

    def descrever(self) -> str:
        if self.produz_vetores_densos():
            return f"{self.modo.value} ({MODELO_DE_VETORES})"
        janela = "1-2" if self.n_max >= 2 else "1"
        return f"{self.modo.value} n={janela}"

    # A pergunta que decide qual classificador pode consumir esta matriz.
    def produz_vetores_densos(self) -> bool:
        return self.modo is ModoVetorizacao.EMBEDDING


# O espaço completo. As esparsas variam a janela de n-grama; a densa não tem
# janela para variar, então entra uma vez só — gerá-la duas vezes produziria
# duas linhas idênticas no ranking, dando a impressão de duas medições.
def todas_as_vetorizacoes() -> list[ConfigVetorizacao]:
    esparsas = [
        ConfigVetorizacao(modo, n)
        for modo in (ModoVetorizacao.BOW, ModoVetorizacao.TFIDF)
        for n in JANELAS_NGRAMA
    ]
    return [*esparsas, ConfigVetorizacao(ModoVetorizacao.EMBEDDING, n_max=1)]


# -----------------------------------------------------------------------------
# Vetorização densa — embeddings pré-treinados
# -----------------------------------------------------------------------------


# Carrega SÓ o vocabulário e os vetores. Todo componente que faz análise —
# tagger, parser, ner, lematizador — fica de fora: nada deles é usado aqui, e
# juntos respondem por quase todo o tempo de carga.
@lru_cache(maxsize=2)
def carregar_vetores(modelo: str):
    import spacy

    try:
        return spacy.load(
            modelo,
            exclude=["tagger", "parser", "ner", "lemmatizer",
                     "morphologizer", "attribute_ruler", "senter", "tok2vec"],
        )
    except OSError as erro:
        raise RuntimeError(
            f"Modelo de vetores `{modelo}` não encontrado. Rode uma vez:\n"
            f"    python -m spacy download {modelo}"
        ) from erro


# -----------------------------------------------------------------------------
# A MESMA ARMADILHA DA VETORIZAÇÃO ESPARSA, NA VERSÃO DENSA — leia antes de mexer
# -----------------------------------------------------------------------------
# O caminho óbvio para vetorizar um documento com spaCy é `nlp(texto).vector`,
# que já devolve a média dos vetores dos tokens. É o caminho ERRADO aqui, e
# erra em silêncio.
#
# `nlp(texto)` TOKENIZA de novo, com as regras do spaCy. Isso jogaria fora a
# tokenização que o pré-processamento escolheu — exatamente o mesmo problema que
# `token_pattern` causa nos vetorizadores do scikit-learn, documentado adiante.
# As três estratégias de tokenização passariam a dar resultado idêntico sob
# embeddings, e o experimento reportaria "não faz diferença" com toda a
# confiança.
#
# Por isso a média é feita à mão sobre `texto.split()`: os tokens já vieram
# prontos do pré-processamento, separados por espaço, e a única coisa que se
# busca no spaCy é o VETOR de cada um.
#
# Token fora do vocabulário não entra na média. Se nenhum token do documento
# tiver vetor, o resultado é o vetor nulo — o que é honesto: não sabemos nada
# sobre aquele documento.
# -----------------------------------------------------------------------------
@lru_cache(maxsize=100_000)
def vetor_do_documento(texto: str, modelo: str) -> tuple[float, ...]:
    vocabulario = carregar_vetores(modelo).vocab
    vetores = [vocabulario[t].vector for t in texto.split() if vocabulario[t].has_vector]
    if not vetores:
        return tuple(np.zeros(vocabulario.vectors.shape[1], dtype="float32").tolist())
    return tuple(np.mean(vetores, axis=0).tolist())


# Adapta a média de embeddings à interface de transformador do scikit-learn,
# para que ela seja uma etapa do Pipeline como qualquer vetorizador.
#
# `fit` não faz nada de propósito, e isso é uma PROPRIEDADE, não uma limitação:
# os vetores são pré-treinados, então não há nada a aprender das dobras de
# treino e não existe vazamento possível. É o oposto do TF-IDF, cujo IDF precisa
# ser aprendido só no treino — a razão de o Pipeline existir.
class VetorizadorDeEmbeddings(BaseEstimator, TransformerMixin):
    # O parâmetro fica em `self.modelo` sem alteração nenhuma. É exigência do
    # `clone()`, que a validação cruzada usa para criar uma cópia limpa a cada
    # dobra: ele reconstrói o objeto a partir dos argumentos do `__init__`.
    def __init__(self, modelo: str = MODELO_DE_VETORES) -> None:
        self.modelo = modelo

    def fit(self, X, y=None):  # noqa: N803 — nomes exigidos pela interface do sklearn
        return self

    def transform(self, X):  # noqa: N803
        return np.array([vetor_do_documento(texto, self.modelo) for texto in X], dtype="float64")

    # O ranking do experimento mostra o tamanho do vocabulário de cada
    # configuração. Para uma vetorização densa esse número é fixo: são sempre as
    # mesmas 300 dimensões, venha o que vier no corpus.
    def get_feature_names_out(self, input_features=None):
        largura = carregar_vetores(self.modelo).vocab.vectors.shape[1]
        return np.array([f"dim_{i}" for i in range(largura)])


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
# de transformação e de tokenização fica em preprocessamento.py, que é o objeto
# do estudo.
#
# Há testes em tests/test_vetorizacao.py que quebram se isto for revertido.
# -----------------------------------------------------------------------------
def construir_vetorizador(
    config: ConfigVetorizacao,
) -> CountVectorizer | TfidfVectorizer | VetorizadorDeEmbeddings:
    if config.modo is ModoVetorizacao.EMBEDDING:
        return VetorizadorDeEmbeddings()

    classe = CountVectorizer if config.modo is ModoVetorizacao.BOW else TfidfVectorizer
    return classe(
        lowercase=False,      # quem decide é o preprocessar
        tokenizer=str.split,  # os tokens já vieram prontos, separados por espaço
        token_pattern=None,   # exigido pelo sklearn quando `tokenizer` é passado
        ngram_range=(1, config.n_max),
    )


# Vetorizador + Naive Bayes, usado pelo EXPERIMENTO como instrumento de medida.
#
# Não confundir com `classificador.construir_classificador`, que monta o modelo
# do produto. Aqui o classificador é a RÉGUA: para comparar formas de preparar
# o texto, tudo o que vem depois precisa ser idêntico — mesmo algoritmo, mesmos
# parâmetros, mesma semente. Naive Bayes serve bem porque é determinístico (sem
# sorteio interno nem otimização iterativa), rápido e funciona com poucos dados.
#
# E o Pipeline não é organização, é CORREÇÃO. Dentro da validação cruzada ele
# garante que o vocabulário e o IDF sejam aprendidos APENAS nas dobras de
# treino, e só então aplicados à dobra de teste. Aprender sobre o dataset
# inteiro seria vazamento de dados: a nota sobe, e sobe mentindo.
#
# POR QUE A RÉGUA NÃO É A MESMA PARA TODOS — E O QUE ISSO CUSTA
# -------------------------------------------------------------
# `MultinomialNB` modela CONTAGEM e, por construção, exige entrada não-negativa:
# ele estima P(termo | classe) a partir de somas por coluna, e uma soma negativa
# não é probabilidade de nada. O scikit-learn recusa a entrada com um erro.
#
# Vetores de embedding têm coordenadas negativas — não é detalhe de escala, é o
# que são: posições num espaço centrado na origem. Não existe variante de Naive
# Bayes que trate contagem esparsa e coordenada densa com a mesma suposição.
# `GaussianNB` é a que corresponde ao caso denso: assume que cada dimensão segue
# uma normal dentro de cada classe, que é a leitura certa de uma coordenada
# contínua.
#
# O CUSTO, declarado: quando o relatório compara `embedding` com `tfidf`, ele
# está comparando DOIS PIPELINES INTEIROS, não duas representações com o resto
# constante. Parte da diferença vem da representação e parte vem do
# classificador, e a medição não separa as duas.
#
# Isso não invalida o número para a decisão prática — o que vai para produção é
# o pipeline inteiro, e é ele que está sendo medido. Invalida a frase "embeddings
# são melhores que TF-IDF", que a medição não sustenta. A comparação entre `bow`
# e `tfidf` continua limpa: mesma régua nos dois lados.
def construir_pipeline_de_medicao(config: ConfigVetorizacao) -> Pipeline:
    classificador = GaussianNB() if config.produz_vetores_densos() else MultinomialNB(alpha=1.0)
    return Pipeline(
        [
            ("vetorizador", construir_vetorizador(config)),
            ("classificador", classificador),
        ]
    )
