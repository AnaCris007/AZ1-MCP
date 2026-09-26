"""API determinística para medir a capacidade interna no RNF10."""

from __future__ import annotations

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


class RespondedorDeterministico:
    def answer(self, message: str, conversation_id: str | None = None, **_) -> ChatReply:
        # Mantém a dependência constante em todos os estágios e limita o volume
        # de linhas sem tornar a rota artificialmente instantânea.
        time.sleep(0.5)
        return ChatReply(
            text=f"Resposta determinística completa para {conversation_id}.",
            modelo="rnf10-controlado",
        )


app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
    subject="rnf10-sintetico",
    email="rnf10@example.com",
    name="RNF10",
    provider="simulador",
    domain_user_id=1,
)
app.dependency_overrides[get_conversa_repository] = lambda: PersistenciaDesligada("isolamento RNF10")
app.dependency_overrides[get_chat_answerer] = lambda: RespondedorDeterministico()
app.dependency_overrides[get_classificador_de_intencao] = lambda: None
app.dependency_overrides[get_agente] = lambda: AgenteDesligado("rodada controlada RNF10")
