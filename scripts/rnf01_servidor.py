"""Aplicação de ensaio do RNF01 com autenticação e auditoria isoladas."""

from __future__ import annotations

import os
import re
import time

from az1_api.dependencies import (
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    require_authenticated_user,
)
from az1_api.main import app
from services.agente_service import AgenteDesligado
from services.auth_service import AuthenticatedUser
from services.chat_service import ChatReply
from services.conversa_repository import PersistenciaDesligada


class RespondedorControlado:
    def answer(self, message: str, conversation_id: str | None = None, **_) -> ChatReply:
        correspondencia = re.search(r"\[delay=(\d+)\]", message)
        atraso = int(correspondencia.group(1)) if correspondencia else 0
        if atraso:
            time.sleep(atraso)
        return ChatReply(text=f"Resposta controlada completa para {conversation_id}.", modelo="rnf01-controlado")


app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
    subject="rnf01-sintetico",
    email="rnf01@example.com",
    name="RNF01",
    provider="simulador",
    domain_user_id=1,
)
app.dependency_overrides[get_conversa_repository] = lambda: PersistenciaDesligada("isolamento RNF01")

if os.environ.get("RNF01_MODO") == "controlado":
    app.dependency_overrides[get_chat_answerer] = lambda: RespondedorControlado()
    app.dependency_overrides[get_classificador_de_intencao] = lambda: None
    app.dependency_overrides[get_agente] = lambda: AgenteDesligado("rodada controlada RNF01")
