# =============================================================================
# preprocessamento.py — Pré-processamento de texto configurável
# =============================================================================
# Três ideias sustentam o módulo:
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
# Quem decide as três coisas é o experimento (ver experimento.py), comparando
# por métrica medida.
#
# Dependências de dados, baixadas uma vez:
#     python -m nltk.downloader stopwords rslp
#     python -m spacy download pt_core_news_sm
# =============================================================================

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache

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
# Os imports ficam dentro das funções, e não no topo do arquivo, para que a
# mensagem de erro seja útil: quem esquecer de baixar os dados vê o comando que
# resolve, em vez de um LookupError cru do NLTK.


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
