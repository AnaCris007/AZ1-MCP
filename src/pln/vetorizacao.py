# Conversão de tokens em matriz numérica.

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

SEMENTE = 42


class ModoVetorizacao(StrEnum):
    BOW = "bow"
    TFIDF = "tfidf"


JANELAS_NGRAMA: tuple[int, ...] = (1, 2)


@dataclass(frozen=True)
class ConfigVetorizacao:
    modo: ModoVetorizacao = ModoVetorizacao.TFIDF
    n_max: int = 1

    def descrever(self) -> str:
        janela = "1-2" if self.n_max >= 2 else "1"
        return f"{self.modo.value} n={janela}"


def todas_as_vetorizacoes() -> list[ConfigVetorizacao]:
    return [
        ConfigVetorizacao(modo, n)
        for modo in (ModoVetorizacao.BOW, ModoVetorizacao.TFIDF)
        for n in JANELAS_NGRAMA
    ]


# Os padrões do sklearn (`lowercase=True` e o `token_pattern`) retokenizariam o
# texto, anulando em silêncio as etapas `minusculas` e `remover_pontuacao` e a
# escolha de tokenizador. Travado por tests/test_vetorizacao.py.
def construir_vetorizador(config: ConfigVetorizacao) -> CountVectorizer | TfidfVectorizer:
    classe = CountVectorizer if config.modo is ModoVetorizacao.BOW else TfidfVectorizer
    return classe(
        lowercase=False,
        tokenizer=str.split,
        token_pattern=None,   # exigido pelo sklearn quando `tokenizer` é passado
        ngram_range=(1, config.n_max),
    )


# Régua do experimento, não confundir com `classificador.construir_classificador`,
# que monta o modelo do produto. O Pipeline mantém vocabulário e IDF restritos às
# dobras de treino, evitando vazamento na validação cruzada.
#
# A régua é a mesma para todas as vetorizações do espaço de busca. Uma vetorização
# nova precisa ser aceita por `MultinomialNB` sem trocar de classificador, senão a
# comparação entre representações deixa de ser identificável.
def construir_pipeline_de_medicao(config: ConfigVetorizacao) -> Pipeline:
    return Pipeline(
        [
            ("vetorizador", construir_vetorizador(config)),
            ("classificador", MultinomialNB(alpha=1.0)),
        ]
    )
