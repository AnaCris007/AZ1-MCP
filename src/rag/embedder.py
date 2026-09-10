from __future__ import annotations

import os
import time
from functools import lru_cache

from google import genai

MODELO_EMBEDDING = "gemini-embedding-001"
TAMANHO_LOTE = 10
_RPM_MAX = 5                      # limite do plano gratuito
_INTERVALO_MIN = 60.0 / _RPM_MAX  # 12s entre chamadas

_ultima_chamada: float = 0.0


def _aguardar_rate_limit() -> None:
    global _ultima_chamada
    decorrido = time.time() - _ultima_chamada
    if decorrido < _INTERVALO_MIN:
        time.sleep(_INTERVALO_MIN - decorrido)
    _ultima_chamada = time.time()


@lru_cache(maxsize=1)
def _cliente() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Defina a variável de ambiente antes de vetorizar."
        )
    return genai.Client(api_key=api_key)


def vetorizar(textos: list[str]) -> list[list[float]]:
    """Converte uma lista de textos em embeddings densos via Gemini."""
    if not textos:
        return []

    cliente = _cliente()
    embeddings: list[list[float]] = []

    for inicio in range(0, len(textos), TAMANHO_LOTE):
        _aguardar_rate_limit()
        lote = textos[inicio: inicio + TAMANHO_LOTE]
        resultado = cliente.models.embed_content(
            model=MODELO_EMBEDDING,
            contents=lote,
        )
        embeddings.extend(e.values for e in resultado.embeddings)

    return embeddings


def vetorizar_um(texto: str) -> list[float]:
    """Converte um único texto em embedding — atalho para buscas."""
    return vetorizar([texto])[0]
