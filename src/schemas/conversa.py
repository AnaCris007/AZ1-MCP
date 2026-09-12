"""Contratos HTTP da leitura da trilha de conversas."""

from __future__ import annotations

from pydantic import BaseModel


class ConversaResumoResponse(BaseModel):
    id: str
    titulo: str
    atualizada_em: str


class ConversasResponse(BaseModel):
    conversas: list[ConversaResumoResponse]


class MensagemResponse(BaseModel):
    ordem: int
    papel: str  # 'usuario' ou 'agente'
    conteudo: str


class MensagensResponse(BaseModel):
    mensagens: list[MensagemResponse]


class AvaliacaoRequest(BaseModel):
    """O juízo sobre uma resposta específica.

    A mensagem é endereçada por `(conversa_id, ordem)` porque o cliente não
    conhece o `mensagem_id`: ele nasce por IDENTITY numa tarefa de fundo, depois
    de a resposta já ter sido enviada.
    """

    conversa_id: str
    ordem: int
    polaridade: str  # 'positiva' | 'negativa'
    motivo: str | None = None
    comentario: str | None = None
