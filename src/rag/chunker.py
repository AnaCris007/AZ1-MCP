from __future__ import annotations

from dataclasses import dataclass

from rag.parsers import TextoExtraido

TAMANHO_CHUNK = 800   # caracteres
SOBREPOSICAO = 200    # caracteres de overlap entre chunks consecutivos


@dataclass(frozen=True)
class Chunk:
    texto: str
    projeto_id: str
    tipo_documento: str
    arquivo_origem: str
    secao: str
    chunk_index: int


def _agrupar_por_arquivo(textos: list[TextoExtraido]) -> list[list[TextoExtraido]]:
    grupos: list[list[TextoExtraido]] = []
    atual: list[TextoExtraido] = []
    for item in textos:
        if atual and item.arquivo_origem != atual[0].arquivo_origem:
            grupos.append(atual)
            atual = []
        atual.append(item)
    if atual:
        grupos.append(atual)
    return grupos


def _chunkar_grupo(
    grupo: list[TextoExtraido],
    tamanho: int,
    sobreposicao: int,
    chunk_idx_inicial: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_idx = chunk_idx_inicial
    buffer: list[str] = []
    buffer_len = 0
    ref = grupo[0]

    for item in grupo:
        buffer.append(item.texto)
        buffer_len += len(item.texto)

        if buffer_len >= tamanho:
            texto_chunk = " ".join(buffer)
            chunks.append(Chunk(
                texto=texto_chunk,
                projeto_id=ref.projeto_id,
                tipo_documento=ref.tipo_documento,
                arquivo_origem=ref.arquivo_origem,
                secao=ref.secao,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1
            # Overlap: últimos SOBREPOSICAO chars como início do próximo chunk
            sobrep = texto_chunk[-sobreposicao:] if sobreposicao else ""
            buffer = [sobrep] if sobrep else []
            buffer_len = len(sobrep)

    if buffer:
        chunks.append(Chunk(
            texto=" ".join(buffer),
            projeto_id=ref.projeto_id,
            tipo_documento=ref.tipo_documento,
            arquivo_origem=ref.arquivo_origem,
            secao=ref.secao,
            chunk_index=chunk_idx,
        ))

    return chunks


def chunkar(
    textos: list[TextoExtraido],
    tamanho: int = TAMANHO_CHUNK,
    sobreposicao: int = SOBREPOSICAO,
) -> list[Chunk]:
    if not textos:
        return []

    chunks: list[Chunk] = []
    for grupo in _agrupar_por_arquivo(textos):
        novos = _chunkar_grupo(grupo, tamanho, sobreposicao, len(chunks))
        chunks.extend(novos)
    return chunks
