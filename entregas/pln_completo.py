# =============================================================================
# pln_completo.py — O pipeline inteiro de PLN em UM arquivo
# =============================================================================
#           ██  ARQUIVO GERADO — NÃO EDITE ESTE ARQUIVO À MÃO  ██
#
# Toda alteração aqui é perdida na próxima geração. A fonte é `src/pln/`:
#
#     edite      src/pln/<modulo>.py
#     regenere   python scripts/gerar_pln_completo.py
#
# `tests/test_entrega_unica.py` falha se este arquivo estiver diferente do que
# o gerador produziria — então uma edição manual não passa despercebida, ela
# quebra a suíte.
#
# POR QUE ELE EXISTE
# ------------------
# É a versão de ENTREGA: roda sem instalar o pacote e sem import nenhum entre
# partes.
#
#     python entregas/pln_completo.py treinar
#     python entregas/pln_completo.py prever "Quais prazos vencem esta semana?"
#     python entregas/pln_completo.py experimento --sem-ordem
#
# O código é o mesmo dos módulos, na ordem em que um depende do outro:
#
#     SEÇÃO 1 — caminhos.py: onde ficam os dados e os resultados
#     SEÇÃO 2 — preprocessamento.py: texto bruto vira tokens
#     SEÇÃO 3 — vetorizacao.py: tokens viram matriz numérica
#     SEÇÃO 4 — classificador.py: o modelo do produto
#     SEÇÃO 5 — experimento.py: a busca do TEXTO: pré-processamento x vetorização
#     SEÇÃO 6 — ajuste_fino.py: a busca do MODELO: variante x suavização x priori
#     SEÇÃO 7 — a linha de comando unificada
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
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, cross_validate
from sklearn.naive_bayes import BernoulliNB, ComplementNB, GaussianNB, MultinomialNB
from sklearn.pipeline import Pipeline

# =============================================================================
# SEÇÃO 1 — CAMINHOS: onde ficam os dados e os resultados
# Fonte: src/pln/caminhos.py
# =============================================================================

# =============================================================================
# caminhos.py — Onde ficam os dados e onde vão parar os resultados
# =============================================================================
# Existe por um motivo concreto: até este arquivo, cada módulo resolvia os
# próprios caminhos com `Path(__file__).resolve().parent / "dados" / ...`,
# repetido em três arquivos. O efeito prático foi que o nome do dataset estava
# escrito ERRADO nos três ao mesmo tempo — `intencoes_exemplo.csv` em vez de
# `intencoes_exemplos.csv` — e o `--prever` quebrava com FileNotFoundError.
# Caminho repetido é caminho que diverge; aqui ele é declarado uma vez.
#
# A DISTINÇÃO QUE ORGANIZA ESTE ARQUIVO: ENTRADA x SAÍDA
# ------------------------------------------------------
# Os dois tipos de arquivo têm ciclos de vida opostos e por isso NÃO moram
# juntos.
#
# DADOS DE ENTRADA são parte do pacote. Versionados, pequenos, alterados por
# pessoas, e sem eles o código não roda. Ficam em `pln/dados/` e viajam dentro
# do wheel — é o que faz o experimento funcionar depois de um `pip install`,
# fora da pasta do repositório.
#
# RESULTADOS são saída de execução. Gerados por máquina, sobrescritos a cada
# rodada, e o código roda perfeitamente sem eles. Ficam em `resultados/`, na
# RAIZ do repositório, fora de `src/`. Manter saída gerada dentro do
# código-fonte é o que fazia um `.joblib` binário aparecer no diff de um
# módulo Python.
#
# POR QUE A RAIZ É PROCURADA, E NÃO FIXADA
# ----------------------------------------
# `resultados/` não pode ser resolvido a partir de `__file__`: uma vez
# instalado, o pacote está em site-packages, onde não existe raiz de
# repositório nenhuma. A busca abaixo sobe a árvore até achar o `pyproject.toml`
# e, se não achar, usa o diretório de trabalho. O comportamento fica previsível
# nos dois cenários: dentro do repositório grava sempre em `<repo>/resultados`,
# de qualquer subpasta; fora dele, grava em `./resultados`.
# =============================================================================



# -----------------------------------------------------------------------------
# Entrada — dados versionados, empacotados junto com o código
# -----------------------------------------------------------------------------

DIR_PACOTE = Path(__file__).resolve().parent


# Normalmente é `pln/dados/`, ao lado deste arquivo — dentro do pacote, seja no
# repositório ou instalado em site-packages.
#
# O fallback existe para o arquivo único de `entregas/`, que é uma cópia gerada
# deste código morando FORA do pacote: lá, `DIR_PACOTE / "dados"` não existe, e
# a única referência possível é o repositório. Sem isso, a entrega rodaria só
# depois de alguém copiar o CSV para o lado dela.
def dir_dados() -> Path:
    ao_lado = DIR_PACOTE / "dados"
    if ao_lado.is_dir():
        return ao_lado

    raiz = encontrar_raiz_do_projeto()
    if raiz is not None and (raiz / "src" / "pln" / "dados").is_dir():
        return raiz / "src" / "pln" / "dados"

    # Nenhum dos dois: devolve o caminho canônico assim mesmo, para que o erro
    # seja um FileNotFoundError apontando o lugar certo em vez de um None.
    return ao_lado


# -----------------------------------------------------------------------------
# Saída — artefatos gerados, fora de src/
# -----------------------------------------------------------------------------


# `pyproject.toml` é o marcador de raiz porque é o arquivo que define o
# projeto: se ele está lá, aquela é a raiz. `.git` serviria, mas some quando
# alguém baixa o código como .zip.
def encontrar_raiz_do_projeto(a_partir_de: Path | None = None) -> Path | None:
    inicio = (a_partir_de or DIR_PACOTE).resolve()
    for diretorio in (inicio, *inicio.parents):
        if (diretorio / "pyproject.toml").is_file():
            return diretorio
    return None


def dir_resultados() -> Path:
    raiz = encontrar_raiz_do_projeto() or Path.cwd()
    return raiz / "resultados"


# -----------------------------------------------------------------------------
# Os caminhos concretos, derivados depois de as funções existirem
# -----------------------------------------------------------------------------

DIR_DADOS = dir_dados()

# O dataset de exemplo. Trocá-lo é um argumento de linha de comando
# (`--dataset`), não uma edição aqui.
DATASET_PADRAO = DIR_DADOS / "intencoes_exemplos.csv"

DIR_RESULTADOS = dir_resultados()

# O modelo treinado que `classificador.py` grava e `--prever` lê.
MODELO_PADRAO = DIR_RESULTADOS / "classificador.joblib"


# Chamado por quem vai ESCREVER. Deixar o mkdir aqui evita que cada módulo
# repita `caminho.parent.mkdir(parents=True, exist_ok=True)` — a mesma
# duplicação que originou o bug documentado no topo deste arquivo.
def garantir_dir_de_resultados() -> Path:
    destino = dir_resultados()
    destino.mkdir(parents=True, exist_ok=True)
    return destino


# =============================================================================
# SEÇÃO 2 — PREPROCESSAMENTO: texto bruto vira tokens
# Fonte: src/pln/preprocessamento.py
# =============================================================================

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


# =============================================================================
# SEÇÃO 3 — VETORIZACAO: tokens viram matriz numérica
# Fonte: src/pln/vetorizacao.py
# =============================================================================

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


# =============================================================================
# SEÇÃO 4 — CLASSIFICADOR: o modelo do produto
# Fonte: src/pln/classificador.py
# =============================================================================

# =============================================================================
# classificador.py — Classificador de intenções com Naive Bayes
# =============================================================================
# Este é o MODELO DO PRODUTO.
#
# DE ONDE VÊM OS PADRÕES — E O QUE AINDA NÃO FOI MEDIDO
# -----------------------------------------------------
# `CONFIG_PRE_PADRAO` e `CONFIG_VET_PADRAO` saíram da varredura exaustiva de
# `experimento.py`, registrada em `resultados/comparativo_preprocessamento.md`.
#
# LEIA A RESSALVA ANTES DE CONFIAR NESSES DOIS. No dataset de exemplo atual, a
# varredura devolve F1-macro 1,0000 com desvio 0,0000 — e não devolve isso para
# a vencedora, devolve para 2261 das 6456 configurações avaliadas. A medição não
# está errada; ela está SATURADA, e uma medição saturada não ordena nada.
#
# A causa está no dataset, não no pipeline: são 300 frases geradas por gabarito,
# com apenas 16 primeiras palavras distintas entre elas, e 77% dos exemplos são
# decididos pela primeira palavra sozinha. A validação cruzada acaba colocando
# frases quase idênticas no treino e no teste ao mesmo tempo, e todo mundo
# acerta tudo. Com 20 exemplos por classe o F1 já é 0,9366; os outros 80 por
# classe não acrescentam dificuldade, só repetição.
#
# Consequência prática: entre as 2261 empatadas, o critério que sobrou foi
# SIMPLICIDADE — a configuração que não faz nada com o texto vence porque
# nenhuma etapa se mostrou capaz de melhorar o que já está em 1,0000. É uma
# escolha defensável (não manter etapa que não paga por si), mas é diferente de
# "esta é a melhor forma de preparar o texto". Para o experimento voltar a
# discriminar, o dataset precisa de frases que ele erre — redação livre, não
# gabarito. Ver a seção de ressalvas em docs/PipelinePLN.md.
#
# `VARIANTE_PADRAO`, `ALPHA_PADRAO` e `FIT_PRIOR_PADRAO` vêm de OUTRA medição, e
# precisam vir: `experimento.py` varre pré-processamento e vetorização com o
# classificador FIXO em `MultinomialNB(alpha=1.0)` — ele nunca comparou
# variantes de Naive Bayes nem valores de suavização. Quem faz isso é
# `ajuste_fino.py`, e o resultado está em `resultados/ajuste_fino.md`:
#
#     python -m pln.ajuste_fino
#
# Na última rodada, 3000 candidatos, `multinomial` levou por 0,0011 sobre
# `bernoulli` e 0,0042 sobre `complement`; a suavização mal se moveu entre 0,01 e
# 1,0 e só piorou em 2,0; e `fit_prior` não fez NENHUMA diferença — coerente com
# as três classes do dataset terem exatamente o mesmo tamanho.
#
# POR QUE NAIVE BAYES — E O QUE SE PERDEU NA TROCA
# ------------------------------------------------
# Este arquivo usava regressão logística. A troca foi feita por medição, e o
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
#   `experimento.py` escolheu o pré-processamento medindo com `MultinomialNB`, e
#   a documentação registrava a ressalva de que a regressão logística poderia
#   preferir outro. Essa ressalva morre aqui. A contrapartida é que o
#   experimento deixa de ser um teste independente do produto — ele agora
#   confirma a si mesmo. Continua valendo como comparação RELATIVA entre
#   pré-processamentos, que é para o que ele serve.
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





SEMENTE = 42


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
    # normalmente apareceria. Em frases curtas isso costuma vencer, e chegou a
    # ser o padrão daqui por esse argumento. `ajuste_fino.py` mediu e ele ficou
    # em SEGUNDO, atrás de `multinomial` por 0,0011 — o argumento era plausível
    # e o número não o confirmou.

    # GAUSSIANO: assume COORDENADA CONTÍNUA. Modela cada dimensão como uma
    # normal dentro de cada classe, estimando média e variância. É a única das
    # quatro que aceita valor negativo — e por isso a única compatível com a
    # vetorização por embeddings, cujos vetores são posições num espaço centrado
    # na origem. Em contrapartida, é péssima em matriz esparsa de contagem:
    # milhares de colunas quase sempre zero não têm distribuição normal nenhuma.

    MULTINOMIAL = "multinomial"
    COMPLEMENT = "complement"
    BERNOULLI = "bernoulli"
    GAUSSIANO = "gaussiano"


_CLASSES_NB = {
    VarianteNB.MULTINOMIAL: MultinomialNB,
    VarianteNB.COMPLEMENT: ComplementNB,
    VarianteNB.BERNOULLI: BernoulliNB,
    VarianteNB.GAUSSIANO: GaussianNB,
}

# As três primeiras contam ocorrência e exigem entrada não-negativa; a última
# lê coordenada contínua e exige entrada densa. A escolha não é livre: ela é
# determinada pela vetorização, e combinar errado não é questão de gosto, é erro.
VARIANTES_PARA_ESPARSO: tuple[VarianteNB, ...] = (
    VarianteNB.MULTINOMIAL,
    VarianteNB.COMPLEMENT,
    VarianteNB.BERNOULLI,
)
VARIANTES_PARA_DENSO: tuple[VarianteNB, ...] = (VarianteNB.GAUSSIANO,)


# Quais variantes fazem sentido para uma dada vetorização.
#
# Usada pelo ajuste fino para não gastar avaliação em combinação impossível, e
# por `construir_classificador` para recusar a combinação com uma mensagem que
# diz o que fazer — em vez do `ValueError: Negative values in data` cru do
# scikit-learn, que não menciona nem embeddings nem Naive Bayes.
def variantes_compativeis(config_vet: ConfigVetorizacao) -> tuple[VarianteNB, ...]:
    return VARIANTES_PARA_DENSO if config_vet.produz_vetores_densos() else VARIANTES_PARA_ESPARSO


# GaussianNB não tem `alpha` nem `fit_prior` — os equivalentes são
# `var_smoothing` e `priors`, com semântica diferente. Passar os parâmetros
# errados levantaria TypeError, então cada família recebe os seus.
def construir_estimador_nb(variante: VarianteNB, alpha: float, fit_prior: bool):
    if variante is VarianteNB.GAUSSIANO:
        # `alpha` entra como `var_smoothing`. Os dois são regularização — uma
        # quantidade somada antes de o número virar probabilidade — mas NÃO são
        # intercambiáveis em escala: `alpha` útil vive perto de 1, e
        # `var_smoothing` tem padrão 1e-9. Passar 1.0 aqui não é "suavizar
        # bastante", é achatar a variância de todas as dimensões e destruir o
        # modelo.
        #
        # Quem varre precisa usar uma grade por variante. `ajuste_fino.py` tem
        # `GRADE_ALPHA` e `GRADE_VAR_SMOOTHING` separadas exatamente por isso.
        return GaussianNB(var_smoothing=alpha)
    return _CLASSES_NB[variante](alpha=alpha, fit_prior=fit_prior)

# -----------------------------------------------------------------------------
# Os padrões
# -----------------------------------------------------------------------------
# ATENÇÃO — estes valores valem para O DATASET DE EXEMPLO. Trocar o dataset os
# invalida, e o conserto são dois comandos, nesta ordem:
#
#     python -m pln.experimento  --dataset seus_dados.csv   # os dois primeiros
#     python -m pln.ajuste_fino  --dataset seus_dados.csv   # os três últimos
#
# Nenhum deles se edita a olho: cada um é o vencedor de uma busca medida, e o
# segundo comando lê o relatório do primeiro.
#
# `ConfigPreprocessamento()` sem argumento nenhum é o texto CRU: nenhuma das seis
# etapas ligada. Está escrito com a tokenização explícita, e não pelos padrões da
# dataclass, porque aqui isso é uma decisão registrada — não uma omissão.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
VARIANTE_PADRAO = VarianteNB.MULTINOMIAL
ALPHA_PADRAO = 1.0
FIT_PRIOR_PADRAO = True


# Adapta `preprocessar` à interface de transformador do scikit-learn.
#
# Com isto, o pré-processamento vira uma etapa do Pipeline em vez de um passo
# solto que alguém precisa lembrar de aplicar. O ganho é que o objeto salvo em
# disco carrega a própria configuração: quem carregar o modelo depois não tem
# como aplicar outra por engano.
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
    compativeis = variantes_compativeis(config_vet)
    if variante not in compativeis:
        densa = config_vet.produz_vetores_densos()
        raise ValueError(
            f"`{variante.value}` não pode ser usado com a vetorização `{config_vet.descrever()}`.\n"
            f"  Ela produz vetores {'densos com valores negativos' if densa else 'esparsos de contagem'}, "
            f"e as variantes compatíveis são: {', '.join(v.value for v in compativeis)}.\n"
            f"  Ver a explicação em `VarianteNB`."
        )

    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", construir_estimador_nb(variante, alpha, fit_prior)),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia por validação cruzada e devolve (F1-macro, relatório, matriz, classes).
#
# O nome diz "classificador" para não colidir com `experimento.medir_configuracao`,
# que também faz validação cruzada mas responde outra pergunta: aquela mede UMA
# CONFIGURAÇÃO e devolve F1 médio e desvio; esta avalia UM MODELO PRONTO e devolve
# o relatório por classe. Os dois já se chamaram `avaliar_com_validacao_cruzada`, e
# juntar os arquivos fazia um sobrescrever o outro em silêncio.
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
# logística que este arquivo usava antes calibrava melhor; foi o que se perdeu
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
    garantir_dir_de_resultados()
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path) -> Pipeline:
    return joblib.load(caminho)


def imprimir_matriz_de_confusao(matriz: list[list[int]], classes: list[str]) -> None:
    largura = max(len(c) for c in classes) + 2
    print("Matriz de confusão — linha = intenção real, coluna = prevista")
    print(" " * largura + "".join(f"{c:>{largura}}" for c in classes))
    for classe, linha in zip(classes, matriz, strict=True):
        print(f"{classe:>{largura}}" + "".join(f"{v:>{largura}}" for v in linha))


def main_classificador(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Treina e avalia o classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--variante", type=VarianteNB, choices=list(VarianteNB),
                        default=VARIANTE_PADRAO, help="variante de Naive Bayes")
    parser.add_argument("--alpha", type=float, default=ALPHA_PADRAO,
                        help="suavização de Laplace/Lidstone")
    parser.add_argument("--sem-priori", action="store_true",
                        help="usa probabilidades a priori uniformes em vez das do treino")
    parser.add_argument("--salvar", type=Path, default=MODELO_PADRAO, help="onde gravar o modelo")
    parser.add_argument("--prever", type=str, default=None, help="classifica uma frase e sai")
    args = parser.parse_args(argv)

    if args.prever is not None:
        if not args.salvar.exists():
            print(f"❌ Modelo não encontrado em {args.salvar}. Treine primeiro:\n"
                  f"    python -m pln.classificador")
            return 1
        intencao, confianca = prever_intencao(carregar_modelo(args.salvar), args.prever)
        print(f"{args.prever!r}\n  -> {intencao}  (confiança {confianca:.1%})")
        return 0

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
    print('Teste: python -m pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


# =============================================================================
# SEÇÃO 5 — EXPERIMENTO: a busca do TEXTO: pré-processamento x vetorização
# Fonte: src/pln/experimento.py
# =============================================================================

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


def main_experimento(argv: list[str] | None = None) -> int:
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


# =============================================================================
# SEÇÃO 6 — AJUSTE_FINO: a busca do MODELO: variante x suavização x priori
# Fonte: src/pln/ajuste_fino.py
# =============================================================================

# =============================================================================
# ajuste_fino.py — Busca dos hiperparâmetros do MODELO DO PRODUTO
# =============================================================================
# O que este script responde, com número em vez de opinião:
#
# 1. Qual variante de Naive Bayes classifica melhor estas intenções?
# 2. Quanta suavização (`alpha`) é a certa para este vocabulário?
# 3. As probabilidades a priori devem vir do treino (`fit_prior`) ou ser
#    uniformes?
# 4. Sob os melhores pré-processamentos, qual vetorização o modelo final
#    prefere — sabendo que ela pode não ser a que a régua do experimento preferiu?
#
# A DIVISÃO DE TRABALHO COM experimento.py
# ----------------------------------------
# São duas perguntas diferentes, e cada script fixa o que o outro varia:
#
#     experimento.py  varia  o texto      (pré-processamento x vetorização)
#                     fixa   o modelo     MultinomialNB(alpha=1.0), a régua
#
#     ajuste_fino.py  varia  o modelo     (variante x suavização x priori)
#                     fixa   o texto      os melhores do experimento
#
# ISSO É UMA BUSCA EM ESTÁGIOS, E ESTÁGIO NÃO ACHA ÓTIMO GLOBAL — a mesma
# objeção que fez a opção `--duas-fases` ser removida de `experimento.py`. A
# diferença que justifica manter aqui é de tamanho, não de método: o produto
# cartesiano completo seria 432 pré-processamentos x 5 vetorizações x variantes
# x 6 valores de suavização x 2 prioris, na casa das dezenas de milhares de
# validações cruzadas. O corte está declarado e é ajustável em uma flag
# (`--top-pre`, e `--top-pre 0` varre TODOS os pré-processamentos do relatório).
#
# De onde vêm os candidatos de texto: do CSV que `experimento.py` grava. Rode o
# experimento primeiro. Sem o arquivo, este script cai numa lista mínima embutida
# e avisa que está fazendo isso.
#
# USO
# ---
#     python -m pln.experimento          # primeiro, para gerar os candidatos
#     python -m pln.ajuste_fino          # depois, para ajustar o modelo
#     python -m pln.ajuste_fino --top-pre 20 --k 10
#     python -m pln.ajuste_fino --top-pre 0     # todos os pré-processamentos
# =============================================================================






# A suavização das variantes de contagem. Abaixo de 1,0 o modelo confia mais nas
# contagens observadas; acima, puxa tudo para a uniforme e apaga as diferenças
# entre classes. O padrão do scikit-learn é 1,0.
GRADE_ALPHA: tuple[float, ...] = (0.01, 0.05, 0.1, 0.5, 1.0, 2.0)

# A suavização da variante gaussiana vive em outra escala inteiramente: é uma
# fração da maior variância, somada a todas as variâncias para estabilizar a
# divisão. O padrão do scikit-learn é 1e-9. Usar aqui a grade de `alpha` seria
# testar seis valores igualmente destrutivos.
GRADE_VAR_SMOOTHING: tuple[float, ...] = (1e-11, 1e-9, 1e-7, 1e-5, 1e-3, 1e-1)

# `fit_prior=False` fixa as prioris em uniformes — o análogo mais próximo do
# `class_weight="balanced"` que Naive Bayes não tem. Só se aplica às variantes
# de contagem.
GRADE_FIT_PRIOR: tuple[bool, ...] = (True, False)

# O mínimo indispensável quando não há relatório do experimento para ler.
PRE_PROCESSAMENTOS_DE_EMERGENCIA: tuple[ConfigPreprocessamento, ...] = (
    ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT),
    ConfigPreprocessamento(minusculas=True, tokenizacao=Tokenizacao.REGEX),
    ConfigPreprocessamento(
        minusculas=True, remover_pontuacao=True,
        stopwords=ModoStopwords.PRESERVAR_NEGACOES, tokenizacao=Tokenizacao.REGEX,
    ),
)


@dataclass(frozen=True)
class Candidato:
    config_pre: ConfigPreprocessamento
    config_vet: ConfigVetorizacao
    variante: VarianteNB
    suavizacao: float
    fit_prior: bool

    def descrever(self) -> str:
        priori = "" if self.variante is VarianteNB.GAUSSIANO else f" prior={'treino' if self.fit_prior else 'unif'}"
        return (
            f"{self.variante.value:>11} s={self.suavizacao:<7g}{priori} | "
            f"{self.config_vet.descrever()} | {self.config_pre.descrever()}"
        )


# O nome carrega o "DoAjuste" porque `experimento.py` tem o seu próprio
# `Resultado`, com outros campos. Enquanto são módulos separados os dois nomes
# curtos conviveriam; no arquivo único de `entregas/`, o segundo apagaria o
# primeiro em silêncio. O gerador recusa a junção quando isso acontece, e a
# saída dele foi o que motivou este nome.
@dataclass
class ResultadoDoAjuste:
    candidato: Candidato
    f1_medio: float
    f1_desvio: float


# -----------------------------------------------------------------------------
# Os candidatos de texto, lidos do relatório do experimento
# -----------------------------------------------------------------------------


# Reconstrói uma `ConfigPreprocessamento` a partir de uma linha do CSV.
#
# O CSV grava cada campo em coluna própria justamente para permitir isto — ler
# de volta sem precisar interpretar a string de descrição, que é para humano.
def config_da_linha(linha: dict[str, str]) -> ConfigPreprocessamento:
    def booleano(nome: str) -> bool:
        return linha[nome].strip().lower() == "true"

    return ConfigPreprocessamento(
        minusculas=booleano("minusculas"),
        remover_acentos=booleano("remover_acentos"),
        remover_pontuacao=booleano("remover_pontuacao"),
        remover_numeros=booleano("remover_numeros"),
        stopwords=ModoStopwords(linha["stopwords"]),
        morfologia=ModoMorfologia(linha["morfologia"]),
        tokenizacao=Tokenizacao(linha["tokenizacao"]),
    )


# Os melhores pré-processamentos distintos do relatório, na ordem do ranking.
#
# Distintos importa: o CSV tem uma linha por (pré-processamento, vetorização),
# então o mesmo texto aparece até cinco vezes seguidas no topo. Sem a
# deduplicação, `--top-pre 5` traria um único pré-processamento cinco vezes.
def carregar_candidatos_de_texto(quantos: int) -> tuple[list[ConfigPreprocessamento], str]:
    caminho = dir_resultados() / "comparativo_preprocessamento.csv"
    if not caminho.is_file():
        return list(PRE_PROCESSAMENTOS_DE_EMERGENCIA), (
            f"⚠️  {caminho.name} não encontrado — usando a lista mínima embutida.\n"
            f"   Rode `python -m pln.experimento` primeiro para ajustar sobre os "
            f"pré-processamentos realmente medidos."
        )

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    distintos: list[ConfigPreprocessamento] = []
    ja_vistos: set[ConfigPreprocessamento] = set()
    for linha in linhas:
        config = config_da_linha(linha)
        if config not in ja_vistos:
            ja_vistos.add(config)
            distintos.append(config)
        if quantos and len(distintos) >= quantos:
            break

    quantidade = "todos os" if not quantos else f"os {len(distintos)} melhores"
    return distintos, f"Pré-processamentos: {quantidade} de {caminho.name} ({len(linhas)} linhas)."


# -----------------------------------------------------------------------------
# O espaço de busca do modelo
# -----------------------------------------------------------------------------


# A grade de suavização depende da variante — ver o comentário das constantes.
def grade_de_suavizacao(variante: VarianteNB) -> tuple[float, ...]:
    return GRADE_VAR_SMOOTHING if variante is VarianteNB.GAUSSIANO else GRADE_ALPHA


# GaussianNB não tem `fit_prior`; varrer os dois valores geraria duas linhas
# idênticas com nomes diferentes, o que é pior do que não varrer.
def grade_de_prior(variante: VarianteNB) -> tuple[bool, ...]:
    return (True,) if variante is VarianteNB.GAUSSIANO else GRADE_FIT_PRIOR


def montar_candidatos(configs_pre: list[ConfigPreprocessamento]) -> list[Candidato]:
    candidatos: list[Candidato] = []
    for config_pre, config_vet in itertools.product(configs_pre, todas_as_vetorizacoes()):
        for variante in variantes_compativeis(config_vet):
            for suavizacao, fit_prior in itertools.product(
                grade_de_suavizacao(variante), grade_de_prior(variante)
            ):
                candidatos.append(Candidato(config_pre, config_vet, variante, suavizacao, fit_prior))
    return candidatos


# Mede um candidato por validação cruzada estratificada.
#
# O pré-processamento é etapa do Pipeline, então ele é reaplicado dentro de cada
# dobra. Custa tempo e é o certo: mantém a garantia de que nada aprendido no
# treino vaza para o teste, e é a mesma disciplina do experimento.
def medir(candidato: Candidato, textos: list[str], rotulos: list[str], k: int) -> ResultadoDoAjuste:
    modelo = construir_classificador(
        config_pre=candidato.config_pre,
        config_vet=candidato.config_vet,
        variante=candidato.variante,
        alpha=candidato.suavizacao,
        fit_prior=candidato.fit_prior,
    )
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    notas = cross_val_score(modelo, textos, rotulos, cv=dobras, scoring="f1_macro")
    desvio = statistics.stdev(notas) if len(notas) > 1 else 0.0
    return ResultadoDoAjuste(candidato, statistics.mean(notas), desvio)


def varrer(candidatos: list[Candidato], textos: list[str], rotulos: list[str], k: int) -> list[ResultadoDoAjuste]:
    resultados: list[ResultadoDoAjuste] = []
    for numero, candidato in enumerate(candidatos, start=1):
        resultados.append(medir(candidato, textos, rotulos, k))
        if sys.stdout.isatty() and numero % 10 == 0:
            print(f"\r  {numero}/{len(candidatos)} candidatos", end="", flush=True)

    if sys.stdout.isatty():
        print(f"\r  {len(candidatos)}/{len(candidatos)} candidatos")

    resultados.sort(key=lambda r: r.f1_medio, reverse=True)
    return resultados


# -----------------------------------------------------------------------------
# Análise
# -----------------------------------------------------------------------------


# O ESPAÇO DE BUSCA TEM DUAS REGIÕES DISJUNTAS, E ISSO MUDA COMO SE COMPARA
# --------------------------------------------------------------------------
# `gaussiano` só existe com vetorização densa; as outras três variantes só
# existem com esparsa. As grades de suavização também são disjuntas — `alpha`
# perto de 1, `var_smoothing` perto de 1e-9.
#
# Uma comparação pareada exige que os grupos comparados sejam completos. Se o
# universo for o espaço inteiro, NENHUM grupo é completo: nenhuma combinação tem
# todas as variantes, porque não pode ter. A primeira versão desta função
# ignorava isso, e o efeito foi a tabela de variante, de suavização e de
# vetorização SUMIREM do relatório sem erro nenhum — exatamente o mesmo defeito
# que `medir_efeito_da_vetorizacao` tinha em experimento.py.
#
# A correção é comparar DENTRO de cada região. Cada tabela sai rotulada com a
# região a que se refere, e comparar as duas entre si é uma pergunta diferente,
# respondida na linha "esparsa vs densa" da recomendação.
def separar_por_familia(resultados: list[ResultadoDoAjuste]) -> list[tuple[str, list[ResultadoDoAjuste]]]:
    esparsos = [r for r in resultados if not r.candidato.config_vet.produz_vetores_densos()]
    densos = [r for r in resultados if r.candidato.config_vet.produz_vetores_densos()]
    return [(nome, grupo) for nome, grupo in (("esparsa", esparsos), ("densa", densos)) if grupo]


# Como cada valor de eixo aparece nas tabelas. Os três tipos que circulam aqui
# imprimem de formas diferentes, e o `str()` cru de um dataclass é ilegível:
# "ConfigVetorizacao(modo=<ModoVetorizacao.TFIDF: 'tfidf'>, n_max=2)" no lugar de
# "tfidf n=1-2".
def rotular(valor) -> str:
    if hasattr(valor, "descrever"):
        return valor.descrever()
    if hasattr(valor, "value"):
        return str(valor.value)
    return str(valor)


# O efeito de um eixo dentro de UMA região, comparado de forma PAREADA: para
# cada combinação dos outros eixos, compara os valores deste entre si.
#
# Média solta não serve: ela compararia amostras diferentes e atribuiria ao eixo
# uma diferença que veio do resto.
def comparar_eixo(resultados: list[ResultadoDoAjuste], eixo: str) -> list[tuple[str, float, int]]:
    outros = [c for c in ("config_pre", "config_vet", "variante", "suavizacao", "fit_prior") if c != eixo]

    grupos: dict[tuple, dict[str, float]] = {}
    for resultado in resultados:
        chave = tuple(getattr(resultado.candidato, campo) for campo in outros)
        grupos.setdefault(chave, {})[rotular(getattr(resultado.candidato, eixo))] = resultado.f1_medio

    rotulos = {r for g in grupos.values() for r in g}
    if len(rotulos) < 2:
        return []  # eixo constante nesta região: não há o que comparar

    completos = [g for g in grupos.values() if len(g) == len(rotulos)]
    if not completos:
        return []

    return sorted(
        ((rotulo, statistics.mean(g[rotulo] for g in completos), len(completos)) for rotulo in rotulos),
        key=lambda linha: linha[1],
        reverse=True,
    )


# A melhor de cada região, para a pergunta que a comparação pareada não responde:
# vale a pena a vetorização densa?
#
# Aqui a comparação é entre os TOPOS, não entre médias, e de propósito. A média
# de uma região inteira mistura combinações boas e absurdas — `var_smoothing=1e-1`
# arrasa a região densa e puxaria a média para baixo por um motivo que não é a
# representação. O que interessa para decidir é o melhor que cada uma alcança.
def melhor_por_familia(resultados: list[ResultadoDoAjuste]) -> list[tuple[str, ResultadoDoAjuste]]:
    return [(nome, max(grupo, key=lambda r: r.f1_medio)) for nome, grupo in separar_por_familia(resultados)]


# Entre as configurações empatadas com a melhor, a mais simples.
#
# Empate aqui é "dentro de um desvio padrão da melhor" — a mesma régua do
# experimento. Simplicidade é, em ordem: menos etapas de pré-processamento,
# vetorização esparsa antes de densa (não depende de baixar modelo de 40 MB), e
# suavização mais próxima do padrão da biblioteca.
def escolher_mais_simples(resultados: list[ResultadoDoAjuste]) -> ResultadoDoAjuste:
    melhor = resultados[0]
    limiar = melhor.f1_medio - melhor.f1_desvio
    empatados = [r for r in resultados if r.f1_medio >= limiar]

    def custo(r: ResultadoDoAjuste) -> tuple:
        c = r.candidato
        padrao = 1e-9 if c.variante is VarianteNB.GAUSSIANO else 1.0
        return (
            len(c.config_pre.etapas_ativas_na_ordem()),
            c.config_vet.produz_vetores_densos(),
            c.config_vet.n_max,
            abs(c.suavizacao - padrao),
            -r.f1_medio,
        )

    return min(empatados, key=custo)


# -----------------------------------------------------------------------------
# Saída
# -----------------------------------------------------------------------------


# `descrever()` usa `|` como separador, e `|` é o que delimita coluna em tabela
# markdown. Sem escapar, uma configuração vira três colunas e a tabela inteira
# se desalinha a partir dali.
def escapar_para_tabela(texto: str) -> str:
    return texto.replace("|", "\\|")


# O bloco de valores prontos para colar em `classificador.py`.
#
# Precisa ser Python VÁLIDO. O `repr()` de um dataclass com enums não é: ele
# imprime `<ModoStopwords.MANTER: 'manter'>`, que não compila, além de listar
# todos os campos no valor padrão. O que sai daqui é o construtor mínimo — só os
# campos que diferem do padrão — e é copiável direto.
def gerar_bloco_de_configuracao(candidato: Candidato) -> list[str]:
    padrao = ConfigPreprocessamento()
    argumentos = [
        f"{campo}={getattr(candidato.config_pre, campo)}"
        for campo in ("minusculas", "remover_acentos", "remover_pontuacao", "remover_numeros")
        if getattr(candidato.config_pre, campo) != getattr(padrao, campo)
    ]
    if candidato.config_pre.stopwords is not padrao.stopwords:
        argumentos.append(f"stopwords=ModoStopwords.{candidato.config_pre.stopwords.name}")
    if candidato.config_pre.morfologia is not padrao.morfologia:
        argumentos.append(f"morfologia=ModoMorfologia.{candidato.config_pre.morfologia.name}")
    # A tokenização entra sempre: é decisão registrada, não omissão.
    argumentos.append(f"tokenizacao=Tokenizacao.{candidato.config_pre.tokenizacao.name}")

    fit_prior = "" if candidato.variante is VarianteNB.GAUSSIANO else f"\nFIT_PRIOR_PADRAO  = {candidato.fit_prior}"
    return [
        "```python",
        f"CONFIG_PRE_PADRAO = ConfigPreprocessamento({', '.join(argumentos)})",
        f"CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.{candidato.config_vet.modo.name}, "
        f"n_max={candidato.config_vet.n_max})",
        f"VARIANTE_PADRAO   = VarianteNB.{candidato.variante.name}",
        f"ALPHA_PADRAO      = {candidato.suavizacao!r}" + fit_prior,
        "```",
    ]

EIXOS_ANALISADOS = ("variante", "suavizacao", "fit_prior", "config_vet")

TITULOS_DOS_EIXOS = {
    "variante": "VARIANTE DE NAIVE BAYES",
    "suavizacao": "SUAVIZAÇÃO",
    "fit_prior": "PROBABILIDADES A PRIORI",
    "config_vet": "VETORIZAÇÃO",
    "config_pre": "PRÉ-PROCESSAMENTO",
}


def imprimir_ranking_do_ajuste(resultados: list[ResultadoDoAjuste], top: int) -> None:
    print(f"\n{'#':>3}  {'F1-macro':>8}  {'±dp':>6}  configuração")
    print("-" * LARGURA)
    for posicao, r in enumerate(resultados[:top], start=1):
        print(f"{posicao:>3}  {r.f1_medio:>8.4f}  {r.f1_desvio:>6.4f}  {r.candidato.descrever()}")


def imprimir_eixos(resultados: list[ResultadoDoAjuste]) -> None:
    for familia, grupo in separar_por_familia(resultados):
        for eixo in EIXOS_ANALISADOS:
            linhas = comparar_eixo(grupo, eixo)
            if not linhas:
                continue
            cabecalho = (f"{TITULOS_DOS_EIXOS[eixo]} — vetorização {familia}, "
                         f"pareado em {linhas[0][2]} combinações")
            print(f"\n{cabecalho:^{LARGURA}}")
            print(f"{'opção':>24}  {'F1 médio':>10}  {'vs melhor':>12}")
            print("-" * LARGURA)
            topo = linhas[0][1]
            for rotulo, media, _ in linhas:
                print(f"{rotulo:>24}  {media:>10.4f}  {media - topo:>+12.4f}")


def escrever_relatorio_do_ajuste(
    resultados: list[ResultadoDoAjuste], escolhido: ResultadoDoAjuste, dataset: Path, k: int, origem: str
) -> Path:
    destino = garantir_dir_de_resultados() / "ajuste_fino.md"
    melhor = resultados[0]

    linhas = [
        "# Ajuste fino do classificador de intenções",
        "",
        f"- Dataset: `{dataset.name}`",
        f"- Validação cruzada estratificada de {k} dobras, semente {SEMENTE}",
        f"- Candidatos avaliados: {len(resultados)}",
        f"- {origem}",
        "",
        "Este relatório ajusta o MODELO. O que preparar do texto é decidido em",
        "`comparativo_preprocessamento.md`, por `experimento.py`.",
        "",
        "## Recomendação",
        "",
        f"- **Melhor absoluta:** {melhor.f1_medio:.4f} ± {melhor.f1_desvio:.4f} — "
        f"`{melhor.candidato.descrever()}`",
        f"- **Mais simples entre as empatadas:** {escolhido.f1_medio:.4f} — "
        f"`{escolhido.candidato.descrever()}`",
        "",
        "### Esparsa contra densa",
        "",
        "O melhor que cada família de vetorização alcança — a comparação que as tabelas",
        "pareadas abaixo não fazem, porque elas comparam DENTRO de cada família.",
        "",
        "| vetorização | melhor F1 | configuração |",
        "|---|---|---|",
        *(f"| {nome} | {topo.f1_medio:.4f} | `{escapar_para_tabela(topo.candidato.descrever())}` |"
          for nome, topo in melhor_por_familia(resultados)),
        "",
        "Valores para `classificador.py`:",
        "",
        *gerar_bloco_de_configuracao(escolhido.candidato),
    ]

    for familia, grupo in separar_por_familia(resultados):
        for eixo in EIXOS_ANALISADOS:
            comparacao = comparar_eixo(grupo, eixo)
            if not comparacao:
                continue
            linhas += [
                "", f"## {TITULOS_DOS_EIXOS[eixo].capitalize()} — vetorização {familia}", "",
                f"Comparação **pareada** em {comparacao[0][2]} combinações idênticas nos demais eixos.",
                "", "| opção | F1 médio | vs melhor |", "|---|---|---|",
            ]
            topo = comparacao[0][1]
            for rotulo, media, _ in comparacao:
                linhas.append(f"| `{escapar_para_tabela(rotulo)}` | {media:.4f} | {media - topo:+.4f} |")

    linhas += ["", "## Ranking (top 30)", "", "| # | F1-macro | ±dp | configuração |", "|---|---|---|---|"]
    for posicao, r in enumerate(resultados[:30], start=1):
        linhas.append(
            f"| {posicao} | {r.f1_medio:.4f} | {r.f1_desvio:.4f} | "
            f"`{escapar_para_tabela(r.candidato.descrever())}` |"
        )

    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def main_ajuste_fino(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ajusta os hiperparâmetros do classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--top", type=int, default=15, help="linhas mostradas no ranking")
    parser.add_argument("--top-pre", type=int, default=5,
                        help="quantos pré-processamentos do experimento entram na busca (0 = todos)")
    args = parser.parse_args(argv)

    textos, rotulos = carregar_dataset(args.dataset)
    configs_pre, origem = carregar_candidatos_de_texto(args.top_pre)
    candidatos = montar_candidatos(configs_pre)

    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(origem)
    print(f"Vetorizações: {len(todas_as_vetorizacoes())}   Candidatos: {len(candidatos)}")
    print(f"Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}\n")

    resultados = varrer(candidatos, textos, rotulos, args.k)

    print(f"\n{'=' * LARGURA}")
    print(f"{'AJUSTE FINO DO MODELO':^{LARGURA}}")
    print("=" * LARGURA)
    imprimir_ranking_do_ajuste(resultados, args.top)
    imprimir_eixos(resultados)

    escolhido = escolher_mais_simples(resultados)
    melhor = resultados[0]
    print(f"\n{'=' * LARGURA}")
    print(f"{'RECOMENDAÇÃO':^{LARGURA}}")
    print("=" * LARGURA)
    print(f"Melhor absoluta : {melhor.f1_medio:.4f}  {melhor.candidato.descrever()}")
    empatados = sum(1 for r in resultados if r.f1_medio >= melhor.f1_medio - melhor.f1_desvio)
    print(f"Dentro de 1 desvio padrão da melhor: {empatados} de {len(resultados)} — empatadas na prática.")
    print(f"Mais simples entre as empatadas: {escolhido.f1_medio:.4f}  {escolhido.candidato.descrever()}")
    print()
    for nome, topo in melhor_por_familia(resultados):
        print(f"Melhor com vetorização {nome:>8}: {topo.f1_medio:.4f}  {topo.candidato.descrever()}")

    destino = escrever_relatorio_do_ajuste(resultados, escolhido, args.dataset, args.k, origem)
    print(f"\nRelatório salvo em:\n  {destino}")
    return 0


# =============================================================================
# SEÇÃO 7 — LINHA DE COMANDO
# =============================================================================
# Os módulos originais têm um `main()` cada: um treina o classificador, o outro
# roda o experimento. Juntá-los faria o segundo `def main` apagar o primeiro em
# silêncio, então o gerador renomeia os dois e põe UM ponto de entrada aqui.
#
# Esta função não reimplementa nada: ela repassa os argumentos restantes para o
# `main` do módulo correspondente. É o que garante que o arquivo único e os
# módulos se comportem igual — não existe segunda cópia da lógica para divergir.
#
#     python entregas/pln_completo.py treinar               == python -m pln.classificador
#     python entregas/pln_completo.py prever "..."          == python -m pln.classificador --prever "..."
#     python entregas/pln_completo.py experimento           == python -m pln.experimento
#     python entregas/pln_completo.py ajuste                == python -m pln.ajuste_fino
# =============================================================================

USO = """uso: pln_completo.py <comando> [opções]

comandos:
  treinar              treina, avalia por validação cruzada e salva o modelo
  prever "<frase>"     classifica uma frase com o modelo salvo
  experimento          busca a melhor preparação do TEXTO
  ajuste               busca os hiperparâmetros do MODELO (rode o experimento antes)

`<comando> --help` mostra as opções de cada um."""


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)

    if not argumentos or argumentos[0] in {"-h", "--help"}:
        print(USO)
        return 0

    comando, resto = argumentos[0], argumentos[1:]

    if comando == "treinar":
        return main_classificador(resto)

    # `prever` é `--prever` do classificador. Fica como subcomando próprio
    # porque `pln_completo.py prever "frase"` lê melhor do que a flag.
    if comando == "prever":
        if not resto:
            print('faltou a frase: pln_completo.py prever "Quais prazos vencem?"')
            return 2
        return main_classificador(["--prever", *resto])

    if comando == "experimento":
        return main_experimento(resto)

    # `ajuste` lê o CSV que `experimento` grava, então a ordem importa.
    if comando == "ajuste":
        return main_ajuste_fino(resto)

    print(f"comando desconhecido: {comando}\n")
    print(USO)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
