"""
preprocessamento.py — Pré-processamento configurável em etapas, ordem e tokenização.

Três ideias sustentam o módulo:

1. Não existe conjunto de etapas universalmente melhor. O que ajuda num corpus
   atrapalha noutro. Nenhuma etapa é obrigatória.

2. A ORDEM também não é dada. Trocar duas etapas de lugar muda o resultado — e,
   em alguns casos, faz uma etapa parar de funcionar. Por isso a ordem é campo
   da configuração, não decisão embutida na função.

3. A TOKENIZAÇÃO é uma escolha, não um detalhe. Separar por espaço, por regex
   ou por regra linguística produz vocabulários diferentes a partir do mesmo
   texto — e é o vocabulário que o classificador enxerga.

Quem decide as três coisas é o experimento (ver experimento.py), comparando por
métrica medida.

Dependências de dados, baixadas uma vez:

    python -m nltk.downloader stopwords rslp
    python -m spacy download pt_core_news_sm
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache

_RE_PONTUACAO = re.compile(r"[^\w\s]", flags=re.UNICODE)
_RE_NUMEROS = re.compile(r"\d+")
_RE_ESPACOS = re.compile(r"\s+")

#: Nomes das etapas ordenáveis. A tupla também define a ORDEM PADRÃO.
#:
#: A tokenização NÃO está aqui de propósito: ela não é uma etapa que se
#: intercala entre as outras, é a operação que converte texto em tokens — e
#: acontece sempre que o pipeline precisa de tokens, além de uma vez ao final.
#: Permutá-la não faria sentido; escolhê-la, sim, e por isso ela é um campo à
#: parte da configuração.
ETAPAS: tuple[str, ...] = (
    "minusculas",
    "remover_acentos",
    "remover_pontuacao",
    "remover_numeros",
    "stopwords",
    "morfologia",
)


class ModoStopwords(StrEnum):
    """As três formas de tratar stopwords, comparáveis na mesma execução.

    A do meio e a da direita costumam ser tratadas como a mesma coisa, e não
    são: a lista do NLTK para português inclui "não", "nem", "sem" e "nunca".
    Em classificação de ASSUNTO isso é inofensivo. Na nossa, de INTENÇÃO, essas
    palavras carregam o sinal — "não atualizou o status" (alerta) e "atualizou
    o status" (transação) viram a mesma frase se a negação sair.
    """

    MANTER = "manter"
    REMOVER_TUDO = "remover_tudo"
    PRESERVAR_NEGACOES = "preservar_negacoes"


class ModoMorfologia(StrEnum):
    """Redução de palavras à sua forma base. As opções são EXCLUSIVAS entre si.

    Stemming e lematização perseguem o mesmo objetivo — fazer "vencendo",
    "vencido" e "vencer" contarem como a mesma evidência — por caminhos
    diferentes, com custos diferentes:

    - STEMMING corta sufixos por regras mecânicas, sem consultar dicionário nem
      olhar o contexto. É rápido e independente de modelo. Produz radicais que
      muitas vezes NÃO são palavras ("vencer" -> "venc"), e junta demais:
      palavras de sentidos distintos podem cair no mesmo radical.

    - LEMATIZAÇÃO mapeia cada palavra para a forma de dicionário ("vencendo" ->
      "vencer", "documentos" -> "documento"), usando classe gramatical e
      contexto. O resultado é sempre palavra real e o agrupamento é mais
      preciso, mas exige um modelo treinado e é uma ordem de grandeza mais
      lenta.

    Aplicar os dois seria redundante e destrutivo — lematizar um radical não
    tem sentido. Por isso são valores de um mesmo campo, e não duas flags.
    """

    NENHUMA = "nenhuma"
    STEMMING = "stemming"
    LEMATIZACAO = "lematizacao"


class Tokenizacao(StrEnum):
    """Como o texto vira lista de tokens. Muda o que o vetorizador enxerga.

    - SPLIT: `str.split()`. Corta em espaço em branco e mais nada. "prazo?" é
      UM token, diferente de "prazo" — então pontuação grudada multiplica o
      vocabulário. É o baseline: o mínimo possível.

    - REGEX: `wordpunct_tokenize` do NLTK, que aplica a expressão
      `\\w+|[^\\w\\s]+`. Separa blocos de letras/dígitos de blocos de
      pontuação, então "prazo?" vira ["prazo", "?"]. Independente de idioma e
      previsível, mas ingênuo com o que não é palavra pura: "R$1.500,00" vira
      sete tokens.

    - LINGUISTICO: o tokenizador do spaCy para português. É baseado em regras
      específicas do idioma — prefixos, sufixos, infixos e uma tabela de
      exceções. Reconhece abreviaturas, mantém números com separador decimal
      inteiros e trata contrações e clíticos como a gramática manda. Mais
      caro, e o único que sabe que está lendo português.
    """

    SPLIT = "split"
    REGEX = "regex"
    LINGUISTICO = "linguistico"


NEGACOES = frozenset(
    {"não", "nao", "nem", "sem", "nunca", "jamais", "nada", "ninguém", "ninguem", "nenhum", "nenhuma"}
)


@dataclass(frozen=True)
class ConfigPreprocessamento:
    """Etapas + ordem + tokenização. `frozen` porque vira chave de dicionário."""

    minusculas: bool = False
    remover_acentos: bool = False
    remover_pontuacao: bool = False
    remover_numeros: bool = False
    stopwords: ModoStopwords = ModoStopwords.MANTER
    morfologia: ModoMorfologia = ModoMorfologia.NENHUMA
    tokenizacao: Tokenizacao = Tokenizacao.SPLIT
    ordem: tuple[str, ...] = ETAPAS

    def __post_init__(self) -> None:
        if set(self.ordem) != set(ETAPAS):
            faltando = set(ETAPAS) - set(self.ordem)
            sobrando = set(self.ordem) - set(ETAPAS)
            raise ValueError(f"ordem inválida — faltando {faltando or '{}'}, sobrando {sobrando or '{}'}")

    def etapa_ligada(self, nome: str) -> bool:
        if nome == "stopwords":
            return self.stopwords is not ModoStopwords.MANTER
        if nome == "morfologia":
            return self.morfologia is not ModoMorfologia.NENHUMA
        return bool(getattr(self, nome))

    def etapas_ativas(self) -> tuple[str, ...]:
        """As etapas ligadas, JÁ na ordem configurada."""
        return tuple(nome for nome in self.ordem if self.etapa_ligada(nome))

    def com_ordem(self, ordem: tuple[str, ...]) -> ConfigPreprocessamento:
        return replace(self, ordem=ordem)

    def rotulo(self) -> str:
        ativas = self.etapas_ativas()
        nomes = []
        for n in ativas:
            if n == "stopwords":
                nomes.append(f"sw:{self.stopwords.value}")
            elif n == "morfologia":
                nomes.append(self.morfologia.value)
            else:
                nomes.append(n)
        etapas = " > ".join(nomes) if nomes else "(texto cru)"
        return f"[tok:{self.tokenizacao.value}] {etapas}"


# ---------------------------------------------------------------------------
# Tokenização
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _tokenizador_spacy():
    """Pipeline vazio do spaCy para português — só o tokenizador.

    `spacy.blank("pt")` carrega as REGRAS do idioma sem carregar modelo
    estatístico nenhum: nada de tagger, parser ou vetores. É rápido de carregar
    e não depende do download do `pt_core_news_sm` — este só é necessário para
    a lematização.
    """
    import spacy

    return spacy.blank("pt")


@lru_cache(maxsize=100_000)
def _tokens_linguistico(texto: str) -> tuple[str, ...]:
    return tuple(t.text for t in _tokenizador_spacy()(texto) if not t.is_space)


def tokenizar(texto: str, modo: Tokenizacao) -> list[str]:
    """Converte texto em tokens segundo a estratégia escolhida."""
    if modo is Tokenizacao.SPLIT:
        return texto.split()

    if modo is Tokenizacao.REGEX:
        from nltk.tokenize import wordpunct_tokenize

        return wordpunct_tokenize(texto)

    return list(_tokens_linguistico(texto))


# ---------------------------------------------------------------------------
# Recursos linguísticos
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _stopwords_nltk() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords

        return frozenset(stopwords.words("portuguese"))
    except LookupError as exc:
        raise RuntimeError(
            "Dados do NLTK não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from exc


@lru_cache(maxsize=1)
def _stemmer():
    """RSLPStemmer — Removedor de Sufixos da Língua Portuguesa (Orengo e Huyck,
    2001), a implementação padrão do NLTK para o idioma. Oito passos de regras."""
    try:
        from nltk.stem import RSLPStemmer

        return RSLPStemmer()
    except LookupError as exc:
        raise RuntimeError(
            "Dados do RSLP não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from exc


@lru_cache(maxsize=1)
def _lematizador():
    """Modelo `pt_core_news_sm` do spaCy, sem parser nem NER.

    A lematização do spaCy depende de classe gramatical: para saber que
    "vencendo" vem de "vencer", o modelo precisa antes reconhecer que é verbo.
    Por isso o tagger e o morphologizer ficam ligados. O parser sintático e o
    reconhecedor de entidades são desligados — não contribuem para o lema e
    respondem pela maior parte do tempo de processamento.
    """
    import spacy

    try:
        return spacy.load("pt_core_news_sm", disable=["parser", "ner"])
    except OSError as exc:
        raise RuntimeError(
            "Modelo de português do spaCy não encontrado. Rode uma vez:\n"
            "    python -m spacy download pt_core_news_sm"
        ) from exc


@lru_cache(maxsize=200_000)
def radical(token: str) -> str:
    """Radical de um token, com cache.

    O cache não é micro-otimização: o experimento reprocessa o mesmo corpus
    milhares de vezes e o RSLP aplica oito passos por palavra. Como o
    vocabulário é pequeno e os tokens se repetem muito, o cache elimina quase
    todo esse trabalho."""
    return _stemmer().stem(token)


@lru_cache(maxsize=100_000)
def lematizar(texto: str) -> str:
    """Lematiza o texto inteiro de uma vez, com cache.

    Diferente do stemming, a lematização NÃO pode ser feita token a token de
    forma isolada: o lema depende da classe gramatical, e a classe depende do
    contexto da frase. "Como" é verbo ou advérbio conforme o que está em volta.
    Por isso a unidade de cache aqui é o texto completo, e não a palavra.

    Consequência a registrar: neste ponto quem tokeniza é o spaCy, porque a
    lematização é indissociável da análise que o modelo faz. A tokenização
    configurada volta a valer na materialização final."""
    return " ".join(t.lemma_ for t in _lematizador()(texto) if not t.is_space)


def remover_acentos(texto: str) -> str:
    """Decompõe cada caractere acentuado e descarta o acento.

    NFKD separa "ç" em "c" + cedilha; o filtro joga fora tudo que for marca de
    combinação (categoria Unicode "Mn"), sobrando o caractere base."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


@lru_cache(maxsize=256)
def _lista_para_comparacao(
    modo: ModoStopwords, ja_aplicadas: tuple[str, ...], morfologia: ModoMorfologia
) -> frozenset[str]:
    """A lista de stopwords transformada como o texto já foi transformado.

    Aqui está a parte sutil da história da ordem. A lista do NLTK é um recurso
    lexical fixo: minúsculas, com acento, palavras inteiras. Se o texto já
    perdeu os acentos, ou já foi reduzido a radicais ou lemas, os tokens deixam
    de casar com a lista crua — a etapa rodaria sem erro e não removeria nada.

    Por isso a lista recebe as MESMAS transformações já aplicadas ao texto. E é
    por depender do que veio antes que esta etapa é sensível à ordem: com
    morfologia antes, a comparação passa a ser entre radicais (ou lemas), e o
    conjunto de palavras removidas muda de verdade.

    O que NÃO é compensado, de propósito: pontuação. Não há como acrescentar
    "o," à lista. Se `stopwords` vier antes de `remover_pontuacao`, tokens
    grudados em vírgula escapam do filtro — e essa perda é um efeito real de
    ordem, que o experimento deve enxergar em vez de esconder.
    """
    palavras = set(_stopwords_nltk())

    if modo is ModoStopwords.PRESERVAR_NEGACOES:
        palavras -= NEGACOES

    if "remover_acentos" in ja_aplicadas:
        palavras = {remover_acentos(p) for p in palavras}

    if "morfologia" in ja_aplicadas:
        if morfologia is ModoMorfologia.STEMMING:
            palavras = {radical(p) for p in palavras}
        elif morfologia is ModoMorfologia.LEMATIZACAO:
            palavras = {lematizar(p) for p in palavras}

    return frozenset(palavras)


def preprocessar(texto: str, config: ConfigPreprocessamento) -> str:
    """Aplica as etapas ligadas na ordem configurada e devolve os tokens unidos.

    O retorno é uma string com os tokens separados por um espaço — formato que
    o vetorizador consome com `tokenizer=str.split`, preservando exatamente a
    tokenização escolhida aqui.

    A tokenização configurada é usada TODA vez que o pipeline precisa de
    tokens: no filtro de stopwords, no stemming e na materialização final. É o
    que faz a escolha do tokenizador ser uma decisão de verdade, e não um
    detalhe do último passo.
    """
    aplicadas: list[str] = []

    for etapa in config.etapas_ativas():
        if etapa == "minusculas":
            texto = texto.lower()
        elif etapa == "remover_acentos":
            texto = remover_acentos(texto)
        elif etapa == "remover_pontuacao":
            texto = _RE_PONTUACAO.sub(" ", texto)
        elif etapa == "remover_numeros":
            texto = _RE_NUMEROS.sub(" ", texto)
        elif etapa == "stopwords":
            lista = _lista_para_comparacao(config.stopwords, tuple(aplicadas), config.morfologia)
            tokens = tokenizar(texto, config.tokenizacao)
            texto = " ".join(t for t in tokens if t.lower() not in lista)
        elif etapa == "morfologia":
            if config.morfologia is ModoMorfologia.STEMMING:
                texto = " ".join(radical(t) for t in tokenizar(texto, config.tokenizacao))
            elif config.morfologia is ModoMorfologia.LEMATIZACAO:
                texto = lematizar(texto)

        aplicadas.append(etapa)

    # Materialização final: o texto vira tokens pelo tokenizador escolhido.
    # Normalizar espaço antes evita que espaços duplicados deixados pelas
    # substituições virem tokens vazios.
    return " ".join(tokenizar(_RE_ESPACOS.sub(" ", texto).strip(), config.tokenizacao))
