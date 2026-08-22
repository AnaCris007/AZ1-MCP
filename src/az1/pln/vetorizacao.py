"""
vetorizacao.py — Conversão de tokens em matriz numérica.

Segunda etapa do pipeline. O pré-processamento decide QUAIS tokens existem
(ver preprocessamento.py); a vetorização decide QUANTO cada token pesa e se
sequências de tokens contam como unidade.

Separado em arquivo próprio porque é uma decisão independente da anterior, com
seu próprio espaço de escolhas — e porque o experimento a trata em uma fase
separada: primeiro fixa a vetorização e busca o melhor pré-processamento,
depois varre a vetorização sobre os melhores pré-processamentos encontrados.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


class ModoVetorizacao(StrEnum):
    """Como o peso de cada termo é calculado.

    - BOW (bag of words): o peso é a contagem bruta do termo no documento.
      Simples e literal. Trata "projeto", que aparece em quase toda frase, com
      o mesmo prestígio de "desapropriação", que aparece em uma só.

    - TFIDF: a contagem é multiplicada pelo IDF, fator que cresce quanto MAIS
      RARO o termo é no corpus. Termo presente em todo documento não distingue
      nada e é achatado; termo raro é destacado. É o conserto exato da fraqueza
      do bag of words — mas em corpus pequeno o IDF fica instável, calculado
      sobre poucas ocorrências, e nem sempre ganha.
    """

    BOW = "bow"
    TFIDF = "tfidf"


#: Janelas de n-grama testadas. `n_max=1` conta só palavras isoladas; `n_max=2`
#: acrescenta os pares de palavras vizinhas.
#:
#: Bigrama existe para capturar o que a palavra sozinha perde: "não atualizou"
#: e "atualizou" têm o mesmo unigrama "atualizou", mas bigramas diferentes. O
#: custo é o vocabulário inflar muito — e vocabulário grande com poucos
#: exemplos leva o modelo a decorar em vez de aprender.
JANELAS_NGRAMA: tuple[int, ...] = (1, 2)


@dataclass(frozen=True)
class ConfigVetorizacao:
    """Uma escolha de vetorização: modo de peso + janela de n-grama."""

    modo: ModoVetorizacao = ModoVetorizacao.TFIDF
    n_max: int = 1

    def rotulo(self) -> str:
        janela = "1-2" if self.n_max >= 2 else "1"
        return f"{self.modo.value} n={janela}"


#: A vetorização usada como RÉGUA na Fase 1.
#:
#: Na primeira fase o objetivo é comparar pré-processamentos, então tudo o que
#: vem depois precisa ficar constante — senão não há como saber se a diferença
#: de resultado veio do texto ou da forma de contá-lo. TF-IDF com unigrama é a
#: escolha convencional para esse papel: é o padrão da área e não favorece
#: nenhuma estratégia de tokenização em particular.
#:
#: A Fase 2 revisita justamente esta escolha, agora sobre os melhores
#: pré-processamentos encontrados.
VETORIZACAO_REFERENCIA = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)


def todas_as_vetorizacoes() -> list[ConfigVetorizacao]:
    """O espaço completo de vetorização: 2 modos x 2 janelas = 4 opções."""
    return [ConfigVetorizacao(modo, n) for modo in ModoVetorizacao for n in JANELAS_NGRAMA]


def construir_vetorizador(config: ConfigVetorizacao) -> CountVectorizer | TfidfVectorizer:
    """Instancia o vetorizador com os padrões do scikit-learn DESLIGADOS.

    ------------------------------------------------------------------
    A ARMADILHA DOS PADRÕES DO SCIKIT-LEARN — leia antes de mexer aqui
    ------------------------------------------------------------------
    Por padrão, CountVectorizer e TfidfVectorizer fazem três coisas por conta
    própria: `lowercase=True` converte tudo para minúsculas, o `token_pattern`
    padrão (r"(?u)\\b\\w\\w+\\b") descarta pontuação e palavras de uma letra, e
    essa mesma expressão substitui qualquer tokenização feita antes.

    Com os padrões, três decisões do nosso experimento virariam enfeite:
    `minusculas` não teria efeito, `remover_pontuacao` também não, e as três
    estratégias de tokenização dariam resultados idênticos — porque o
    vetorizador retokenizaria tudo do seu jeito. O experimento reportaria "não
    faz diferença" para as três, medindo errado com toda a confiança.

    Por isso `lowercase=False` e `tokenizer=str.split`: o vetorizador apenas
    separa nos espaços que o pré-processamento já produziu e conta. Toda
    decisão de transformação e de tokenização fica em preprocessamento.py,
    que é o objeto do estudo.
    ------------------------------------------------------------------
    """
    classe = CountVectorizer if config.modo is ModoVetorizacao.BOW else TfidfVectorizer
    return classe(
        lowercase=False,      # quem decide é o preprocessar
        tokenizer=str.split,  # os tokens já vieram prontos, separados por espaço
        token_pattern=None,   # exigido pelo sklearn quando `tokenizer` é passado
        ngram_range=(1, config.n_max),
    )


def construir_pipeline(config: ConfigVetorizacao) -> Pipeline:
    """Vetorizador + classificador, como um Pipeline do scikit-learn.

    O classificador é a RÉGUA, não o produto. Para comparar formas de preparar
    o texto, tudo o que vem depois precisa ser idêntico — mesmo algoritmo,
    mesmos parâmetros, mesma semente. Naive Bayes multinomial serve bem: é
    determinístico (sem sorteio interno nem otimização iterativa), rápido e
    funciona com poucos dados.

    E o Pipeline não é organização, é CORREÇÃO. Dentro da validação cruzada ele
    garante que o vocabulário e o IDF sejam aprendidos APENAS nas dobras de
    treino, e só então aplicados à dobra de teste. Aprender sobre o dataset
    inteiro seria vazamento de dados: a nota sobe, e sobe mentindo.
    """
    return Pipeline(
        [
            ("vetorizador", construir_vetorizador(config)),
            ("classificador", MultinomialNB(alpha=1.0)),
        ]
    )
