"""Instância controlada da API para a campanha RNF05."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

import uvicorn
from fastapi import Request

from az1_api.dependencies import (
    AuthAPIError,
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    require_authenticated_user,
)
from az1_api.main import app
from pln.entidades import EntidadesExtraidas
from pln.intencao import IntencaoDetectada
from rag.retriever import ResultadoBusca
from services.agente_service import RespostaDoAgente, ResultadoAcao
from services.auth_service import AuthenticatedUser
from services.chat_service import ChatReceptionError, ChatReceptionErrorCode, ChatReply
from services.conversa_repository import PersistenciaDesligada


SAIDA = Path(os.environ["RNF05_OUTPUT_DIR"])
MASSA = json.loads((SAIDA / "massa.json").read_text(encoding="utf-8"))
POR_MENSAGEM = {c["mensagem"]: c for c in MASSA}
POR_CONVERSA = {c["conversation_id"]: c for c in MASSA}
INSTANCE_ID = str(uuid.uuid4())
LOCK = threading.Lock()


def registrar(nome: str, dado: dict[str, object]) -> None:
    with LOCK, (SAIDA / nome).open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(dado, ensure_ascii=False) + "\n")


class Classificador:
    def __call__(self, texto: str) -> IntencaoDetectada:
        caso = POR_MENSAGEM[texto]
        intencao = caso["intencao_esperada"]
        registrar(
            "classificacoes_servidor.jsonl",
            {"id": caso["id"], "intencao": intencao, "instance_id": INSTANCE_ID},
        )
        return IntencaoDetectada(prevista=intencao, confianca=0.97)


class AgenteSemAcao:
    def executar(self, *, deteccao, texto) -> RespostaDoAgente:
        return RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas())


class Respondedor:
    def answer(self, message: str, conversation_id: str | None = None, **_) -> ChatReply:
        caso = POR_MENSAGEM[message]
        if caso["id"] == "RNF05-N03":
            raise ChatReceptionError(ChatReceptionErrorCode.SERVICE_UNAVAILABLE)
        fontes = tuple(
            ResultadoBusca(
                texto=f["trecho"],
                score=f["score"],
                projeto_id=f["projeto_id"],
                tipo_documento=f["tipo_documento"],
                secao=f["secao"],
                arquivo_origem=f["arquivo_origem"],
                chunk_id=f["chunk_id"],
            )
            for f in caso["fontes_esperadas"]
        )
        return ChatReply(
            text=caso["resposta_bruta"],
            fontes=fontes,
            resultado="sucesso",
            modelo="controlado-rnf05",
        )


def autenticar(request: Request) -> AuthenticatedUser:
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if token not in {"rnf05-react-valido", "rnf05-python-valido"}:
        raise AuthAPIError()
    cliente = "react" if "react" in token else "python"
    return AuthenticatedUser(
        subject=f"rnf05-{cliente}",
        email=f"rnf05-{cliente}@example.com",
        name=f"Cliente {cliente}",
        provider="controlado",
    )


@app.middleware("http")
async def evidenciar_requisicao(request: Request, call_next):
    if request.url.path != "/api/v1/chat":
        return await call_next(request)
    corpo = await request.body()
    try:
        payload = json.loads(corpo)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    caso = POR_CONVERSA.get(str(payload.get("conversation_id")), {})
    auth = request.headers.get("authorization", "")
    cliente = "react" if "react" in auth else "python" if "python" in auth else "desconhecido"
    response = await call_next(request)
    registrar(
        "requisicoes_servidor.jsonl",
        {
            "id": caso.get("id"),
            "cliente": cliente,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "instance_id": INSTANCE_ID,
            "authorization": "presente" if auth else "ausente",
        },
    )
    response.headers["X-RNF05-Instance"] = INSTANCE_ID
    return response


app.dependency_overrides[get_chat_answerer] = Respondedor
app.dependency_overrides[get_classificador_de_intencao] = Classificador
app.dependency_overrides[get_agente] = AgenteSemAcao
app.dependency_overrides[get_conversa_repository] = lambda: PersistenciaDesligada("RNF05")
app.dependency_overrides[require_authenticated_user] = autenticar

(SAIDA / "servidor.json").write_text(
    json.dumps(
        {"pid": os.getpid(), "instance_id": INSTANCE_ID, "porta": 8001}, indent=2
    ),
    encoding="utf-8",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
