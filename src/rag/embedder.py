# Vetorização de texto para o índice semântico.
#
# DIMENSÃO: 1536, E NÃO OS 3072 NATIVOS
# -------------------------------------
# O `gemini-embedding-001` devolve 3072 dimensões por padrão, mas o pgvector só
# indexa até 2000 com HNSW ou IVFFlat. Acima disso a coluna existe e aceita
# dados, porém `create_index` falha — e toda busca vira varredura sequencial da
# coleção inteira, com latência crescendo linear com o tamanho da base.
#
# O modelo é treinado com Matryoshka Representation Learning, então truncar não
# descarta informação uniformemente: as primeiras coordenadas concentram o
# sinal. O que a truncagem exige é RENORMALIZAR — só a saída de 3072 vem
# normalizada de fábrica, e a similaridade de cosseno do índice pressupõe
# vetores unitários.
#
# TROCAR ESTE VALOR EXIGE RECRIAR A COLEÇÃO E REEMBEDAR TUDO.
#
# TASK TYPE
# ---------
# Documento e consulta são vetorizados com tarefas diferentes
# (`RETRIEVAL_DOCUMENT` e `RETRIEVAL_QUERY`). O modelo projeta cada lado no
# espaço em que eles se aproximam; usar a mesma tarefa nos dois degrada a
# recuperação em silêncio, sem erro nenhum. Mudar a tarefa também invalida o
# índice existente.
#
# LIMITE DE REQUISIÇÕES
# ---------------------
# O plano gratuito permite 5 chamadas por minuto, o que impõe 12 s entre elas.
# Isso está no caminho de cada busca, então é o gargalo de latência do produto
# inteiro — o classificador de intenções responde em 0,5 ms, quatro ordens de
# grandeza abaixo. Duas defesas aqui: o cache de consultas, que evita a chamada
# quando a pergunta se repete, e a reserva de vaga sob trava, que faz N threads
# concorrentes pegarem N vagas distintas em vez de disputarem a mesma.
#
# A correção de verdade é cota paga no caminho de leitura.

from __future__ import annotations

import math
import os
import threading
import time
from functools import lru_cache

from google import genai
from google.genai import types

MODELO_EMBEDDING = "gemini-embedding-001"

# Precisa caber no limite de 2000 do índice do pgvector. É a fonte única da
# verdade: `indexador` importa daqui em vez de declarar a própria constante.
DIMENSAO_EMBEDDING = 1536

TAREFA_DOCUMENTO = "RETRIEVAL_DOCUMENT"
TAREFA_CONSULTA = "RETRIEVAL_QUERY"

TAMANHO_LOTE = 10

# Sem timeout explícito, uma chamada pendurada segura a thread para sempre e
# consome o orçamento de 15 s do RNF01 inteiro.
TIMEOUT_MS = 30_000

# Quantas consultas distintas ficam em cache. Perguntas de usuário se repetem
# muito, e cada acerto economiza uma chamada de 12 s.
TAMANHO_CACHE_DE_CONSULTAS = 1024

_RPM_MAX = 5                      # limite do plano gratuito
_INTERVALO_MIN = 60.0 / _RPM_MAX  # 12s entre chamadas

_trava = threading.Lock()
_proxima_vaga: float = 0.0


# Reserva a próxima vaga sob trava e dorme FORA dela.
#
# A versão anterior lia e escrevia uma global sem trava: sob concorrência,
# várias threads liam o mesmo valor, todas concluíam que podiam chamar, e a
# cota real estourava. Dormir segurando a trava também não serve — serializaria
# o cálculo junto com a espera, e a enésima thread esperaria 12×N segundos sem
# que ninguém tivesse reservado nada.
#
# `monotonic` e não `time()`: ajuste de relógio não pode liberar ou travar a fila.
def _aguardar_vaga() -> None:
    global _proxima_vaga
    with _trava:
        agora = time.monotonic()
        minha_vaga = max(agora, _proxima_vaga)
        _proxima_vaga = minha_vaga + _INTERVALO_MIN

    espera = minha_vaga - time.monotonic()
    if espera > 0:
        time.sleep(espera)


@lru_cache(maxsize=1)
def _cliente() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Defina a variável de ambiente antes de vetorizar."
        )
    return genai.Client(api_key=api_key)


# Só a saída de 3072 vem normalizada; qualquer truncagem precisa desta etapa,
# senão a distância de cosseno do índice compara vetores de módulos diferentes.
def normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(v * v for v in vetor))
    if norma == 0.0:
        return list(vetor)
    return [v / norma for v in vetor]


def _chamar_api(textos: list[str], tarefa: str) -> list[list[float]]:
    cliente = _cliente()
    embeddings: list[list[float]] = []

    for inicio in range(0, len(textos), TAMANHO_LOTE):
        _aguardar_vaga()
        lote = textos[inicio: inicio + TAMANHO_LOTE]
        resultado = cliente.models.embed_content(
            model=MODELO_EMBEDDING,
            contents=lote,
            config=types.EmbedContentConfig(
                task_type=tarefa,
                output_dimensionality=DIMENSAO_EMBEDDING,
                http_options=types.HttpOptions(timeout=TIMEOUT_MS),
            ),
        )
        embeddings.extend(normalizar(list(e.values)) for e in resultado.embeddings)

    return embeddings


def vetorizar_documentos(textos: list[str]) -> list[list[float]]:
    """Vetoriza trechos de documento para indexação."""
    if not textos:
        return []
    return _chamar_api(textos, TAREFA_DOCUMENTO)


# Cacheia tupla, e não lista: `lru_cache` devolveria sempre o mesmo objeto
# mutável, e um chamador que o alterasse corromperia as consultas seguintes.
@lru_cache(maxsize=TAMANHO_CACHE_DE_CONSULTAS)
def _consulta_cacheada(texto: str) -> tuple[float, ...]:
    return tuple(_chamar_api([texto], TAREFA_CONSULTA)[0])


def vetorizar_consulta(texto: str) -> list[float]:
    """Vetoriza uma pergunta de busca. Repetições saem do cache, sem chamar a API."""
    return list(_consulta_cacheada(texto))


def limpar_cache_de_consultas() -> None:
    """Esvazia o cache. Necessário em teste e após reindexar com outra configuração."""
    _consulta_cacheada.cache_clear()
