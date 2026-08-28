# Pré-processamento de texto configurável: etapas, ordem e tokenização são
# campos da configuração, não decisões embutidas.
#
# Dependências de dados, baixadas uma vez:
#     python -m nltk.downloader stopwords rslp
#     python -m spacy download pt_core_news_sm

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache

# Substitui por espaço, não por vazio: senão "prazo,marco" colaria num token
# inexistente no corpus.
_PONTUACAO = re.compile(r"[^\w\s]", flags=re.UNICODE)
_NUMEROS = re.compile(r"\d+")
_ESPACOS_REPETIDOS = re.compile(r"\s+")

# Etapas ordenáveis, nesta ordem por padrão. A tokenização fica fora porque não
# se intercala entre elas: é aplicada toda vez que o pipeline precisa de tokens.
ETAPAS: tuple[str, ...] = (
    "minusculas",
    "remover_acentos",
    "remover_pontuacao",
    "remover_numeros",
    "stopwords",
    "morfologia",
)


class ModoStopwords(StrEnum):
    # A lista do NLTK inclui "não", "nem", "sem" e "nunca", que carregam o sinal
    # da intenção — daí o terceiro modo.
    MANTER = "manter"
    REMOVER_TUDO = "remover_tudo"
    PRESERVAR_NEGACOES = "preservar_negacoes"


class ModoMorfologia(StrEnum):
    # Valores de um campo, e não flags: lematizar um radical não tem sentido.
    NENHUMA = "nenhuma"
    STEMMING = "stemming"
    LEMATIZACAO = "lematizacao"


class Tokenizacao(StrEnum):
    SPLIT = "split"
    REGEX = "regex"
    LINGUISTICO = "linguistico"


# As variantes sem acento existem porque a etapa pode rodar depois da remoção de
# acentos, e a comparação é literal.
NEGACOES = frozenset(
    {"não", "nao", "nem", "sem", "nunca", "jamais", "nada", "ninguém", "ninguem", "nenhum", "nenhuma"}
)


# `frozen` porque a configuração é usada como chave de dicionário no experimento.
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
        # Sem esta validação, uma etapa ausente da ordem nunca rodaria e não
        # haveria erro.
        if set(self.ordem) != set(ETAPAS):
            faltando = set(ETAPAS) - set(self.ordem)
            sobrando = set(self.ordem) - set(ETAPAS)
            raise ValueError(f"ordem inválida — faltando {faltando or '{}'}, sobrando {sobrando or '{}'}")

    def etapa_esta_ligada(self, nome: str) -> bool:
        if nome == "stopwords":
            return self.stopwords is not ModoStopwords.MANTER
        if nome == "morfologia":
            return self.morfologia is not ModoMorfologia.NENHUMA
        return bool(getattr(self, nome))

    def etapas_ativas_na_ordem(self) -> tuple[str, ...]:
        return tuple(nome for nome in self.ordem if self.etapa_esta_ligada(nome))

    def copiar_com_outra_ordem(self, ordem: tuple[str, ...]) -> ConfigPreprocessamento:
        return replace(self, ordem=ordem)

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


# `spacy.blank` carrega só as regras do idioma, sem modelo estatístico — não
# depende do download do `pt_core_news_sm`.
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


# Imports adiados nas três funções abaixo para trocar o erro cru da biblioteca
# pelo comando de download que resolve.
@lru_cache(maxsize=1)
def carregar_stopwords_do_nltk() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords

        return frozenset(stopwords.words("portuguese"))
    except LookupError as erro:
        raise RuntimeError(
            "Dados do NLTK não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from erro


@lru_cache(maxsize=1)
def carregar_stemmer_rslp():
    try:
        from nltk.stem import RSLPStemmer

        return RSLPStemmer()
    except LookupError as erro:
        raise RuntimeError(
            "Dados do RSLP não encontrados. Rode uma vez:\n    python -m nltk.downloader stopwords rslp"
        ) from erro


# Tagger e morphologizer ficam ligados porque o lema depende da classe
# gramatical; parser e NER são desligados por não contribuírem para o lema.
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


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


@lru_cache(maxsize=200_000)
def reduzir_palavra_ao_radical(palavra: str) -> str:
    return carregar_stemmer_rslp().stem(palavra)


# O cache é por texto, e não por palavra, porque o lema depende do contexto da
# frase. Aqui quem tokeniza é o spaCy; a tokenização configurada volta a valer
# na materialização final de `preprocessar`.
@lru_cache(maxsize=100_000)
def lematizar(texto: str) -> str:
    modelo = carregar_modelo_de_lematizacao_do_spacy()
    return " ".join(token.lemma_ for token in modelo(texto) if not token.is_space)


# A lista do NLTK vem em minúsculas, com acento e em palavras inteiras. Sem
# aplicar a ela as mesmas transformações já feitas no texto, os tokens não casam
# e a etapa roda sem remover nada.
#
# Pontuação não é compensada: não há como acrescentar "o," à lista. Stopwords
# antes de `remover_pontuacao` deixa escapar tokens grudados em vírgula, e isso é
# efeito real da ordem.
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


# Devolve os tokens unidos por espaço, formato que o vetorizador consome com
# `tokenizer=str.split` — é o que preserva a tokenização escolhida aqui.
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

    # Sem normalizar o espaço, as substituições acima deixariam tokens vazios.
    texto_limpo = _ESPACOS_REPETIDOS.sub(" ", texto).strip()
    return " ".join(tokenizar(texto_limpo, config.tokenizacao))
