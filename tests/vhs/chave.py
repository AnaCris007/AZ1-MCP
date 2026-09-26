"""Derivação da chave de uma gravação.

O item 2 do contrato da Seção 6.4.3 define o que separa uma gravação de outra:
provedor, modelo, cenário e versão de contrato organizam as pastas; dentro
delas, o que distingue duas chamadas do mesmo provedor é o conteúdo semântico
da requisição — para STT, o hash do áudio, o idioma, o modelo e os termos; para
chat, a mensagem exata, a instrução e os parâmetros; para TTS, texto, voz,
modelo e formato; para embeddings, texto, modelo e dimensão.

A regra que o plano impõe sobre esses atributos é negativa, e é ela que orienta
este módulo: **não normalizar diferenças semanticamente relevantes**. Por isso
nada aqui faz `strip()`, `lower()` ou remoção de acento no texto de entrada. Uma
instrução de sistema que mudou de maiúscula mudou de chave, e é assim que TI-52
exige que seja — o registro anterior não pode ser reaproveitado quando idioma,
modelo ou instrução mudam.

O digest usa SHA-256 sobre JSON canônico, e não a `hash()` embutida do Python,
que é aleatorizada por processo: o item 4 do contrato exige que o replay
funcione em um processo novo, o que seria impossível com uma chave instável
entre execuções.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

# Um segmento de caminho não pode carregar barra, dois-pontos ou espaço: o nome
# de modelo do Google chega como "models/gemini-2.5-flash", e viraria um nível
# de pasta acidental. A troca é só na representação em disco — o valor original
# continua inteiro dentro do digest.
_INSEGURO = re.compile(r"[^A-Za-z0-9._-]+")

VERSAO_CONTRATO_PADRAO = "v1"


def _seguro(segmento: str) -> str:
    return _INSEGURO.sub("-", segmento).strip("-") or "sem-nome"


@dataclass(frozen=True)
class ChaveVhs:
    """Identidade de uma gravação: onde ela mora e o que a distingue."""

    provedor: str
    modelo: str
    cenario: str
    versao_contrato: str
    atributos: tuple[tuple[str, str], ...]

    @classmethod
    def construir(
        cls,
        *,
        provedor: str,
        modelo: str,
        cenario: str,
        atributos: Mapping[str, object],
        versao_contrato: str = VERSAO_CONTRATO_PADRAO,
    ) -> ChaveVhs:
        """Monta a chave a partir de um mapa de atributos de qualquer tipo.

        Os valores são convertidos para texto e ordenados por nome, para que o
        digest não dependa da ordem em que o chamador escreveu o dicionário.
        Ordenar as chaves do mapa não é normalizar conteúdo: o valor de cada
        atributo entra como veio.
        """
        itens = tuple(sorted((nome, str(valor)) for nome, valor in atributos.items()))
        return cls(
            provedor=provedor,
            modelo=modelo,
            cenario=cenario,
            versao_contrato=versao_contrato,
            atributos=itens,
        )

    @property
    def digest(self) -> str:
        corpo = json.dumps(
            {
                "provedor": self.provedor,
                "modelo": self.modelo,
                "cenario": self.cenario,
                "versao_contrato": self.versao_contrato,
                "atributos": dict(self.atributos),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(corpo.encode("utf-8")).hexdigest()[:16]

    @property
    def caminho_relativo(self) -> Path:
        """Caminho da fita dentro da raiz de gravações."""
        return Path(
            _seguro(self.provedor),
            _seguro(self.modelo),
            _seguro(self.cenario),
            _seguro(self.versao_contrato),
            f"{self.digest}.yaml",
        )

    def descricao(self) -> str:
        """Texto curto para mensagem de erro, sem despejar o conteúdo da massa."""
        return f"{self.provedor}/{self.modelo}/{self.cenario}@{self.versao_contrato}#{self.digest}"


# ---------------------------------------------------------------------------
# Construtores por provedor
# ---------------------------------------------------------------------------
# Existem quatro, e não um genérico, porque o conjunto de atributos relevantes é
# diferente em cada um — e escrever esse conjunto à mão em cada teste é como se
# perde a sensibilidade que TI-52 cobra.


def chave_stt(
    *,
    audio: bytes,
    idioma: str,
    modelo: str,
    termos: Sequence[str] = (),
    cenario: str,
    provedor: str = "deepgram",
    versao_contrato: str = VERSAO_CONTRATO_PADRAO,
) -> ChaveVhs:
    """Chave de uma transcrição: hash do áudio, idioma, modelo e termos.

    O áudio entra como hash porque o conteúdo binário não cabe em um nome de
    arquivo; os termos entram na ordem em que serão enviados ao SDK, sem
    ordenação, porque é essa a sequência que o provedor recebe.
    """
    return ChaveVhs.construir(
        provedor=provedor,
        modelo=modelo,
        cenario=cenario,
        versao_contrato=versao_contrato,
        atributos={
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
            "idioma": idioma,
            "termos": "|".join(termos),
        },
    )


def chave_chat(
    *,
    mensagem: str,
    instrucao: str,
    modelo: str,
    parametros: Mapping[str, object] | None = None,
    cenario: str,
    provedor: str = "gemini",
    versao_contrato: str = VERSAO_CONTRATO_PADRAO,
) -> ChaveVhs:
    """Chave de uma resposta de chat: mensagem exata, instrução e parâmetros."""
    return ChaveVhs.construir(
        provedor=provedor,
        modelo=modelo,
        cenario=cenario,
        versao_contrato=versao_contrato,
        atributos={
            "mensagem": mensagem,
            "instrucao": instrucao,
            "parametros": json.dumps(dict(parametros or {}), sort_keys=True, ensure_ascii=False),
        },
    )


def chave_tts(
    *,
    texto: str,
    voz: str,
    modelo: str,
    formato: str,
    cenario: str,
    provedor: str = "gemini-tts",
    versao_contrato: str = VERSAO_CONTRATO_PADRAO,
) -> ChaveVhs:
    """Chave de uma síntese de fala: texto, voz, modelo e formato."""
    return ChaveVhs.construir(
        provedor=provedor,
        modelo=modelo,
        cenario=cenario,
        versao_contrato=versao_contrato,
        atributos={"texto": texto, "voz": voz, "formato": formato},
    )


def chave_embedding(
    *,
    texto: str,
    modelo: str,
    dimensao: int,
    cenario: str,
    provedor: str = "gemini-embedding",
    versao_contrato: str = VERSAO_CONTRATO_PADRAO,
) -> ChaveVhs:
    """Chave de um embedding: texto, modelo e dimensão.

    A dimensão entra porque o RAG está configurado em 3072 (Seção 6.4.4): um
    vetor gravado em outra dimensão não é reaproveitável, e sem este atributo a
    incompatibilidade só apareceria na inserção em `vecs`.
    """
    return ChaveVhs.construir(
        provedor=provedor,
        modelo=modelo,
        cenario=cenario,
        versao_contrato=versao_contrato,
        atributos={"texto": texto, "dimensao": dimensao},
    )
