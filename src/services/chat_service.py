from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol

from rag.retriever import ResultadoBusca

MAX_MESSAGE_LENGTH = 4000


class RespostaDoModelo(Protocol):
    """O que um `ChatModel` devolve: o texto e o que o fundamentou.

    Estrutural, e não a classe concreta de `gemini_service`, porque este módulo
    é importado por ele — herdar a classe daqui fecharia um ciclo de import.
    """

    texto: str
    fontes: tuple[ResultadoBusca, ...]
    resultado: str
    modelo: str


class ChatModel(Protocol):
    # `conversation_id` é POR PALAVRA-CHAVE de propósito. Acrescentado
    # posicionalmente, ele quebrou todos os dublês que já implementavam o
    # protocolo com a assinatura antiga — `generate_reply(self, message)` —, e
    # quebrou com TypeError em tempo de execução, não de verificação, porque
    # `Protocol` não é checado. Palavra-chave mantém essa porta fechada para o
    # próximo parâmetro também.
    def generate_reply(
        self, message: str, *, conversation_id: str | None = None
    ) -> RespostaDoModelo: ...


class ChatModelUnavailableError(Exception):
    pass


class ChatReceptionErrorCode(Enum):
    EMPTY_MESSAGE = auto()
    MESSAGE_TOO_LONG = auto()
    SERVICE_UNAVAILABLE = auto()


class ChatReceptionError(Exception):
    def __init__(self, code: ChatReceptionErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class ChatReply:
    text: str
    # As fontes atravessam até a rota por dois motivos: citar na resposta (RNF12)
    # e gravar em `auditoria.mensagem_fonte` (RNF04). A ordem é a mesma da
    # numeração usada no prompt, então `[2]` na resposta é `fontes[1]`.
    fontes: tuple[ResultadoBusca, ...] = field(default_factory=tuple)
    # Os dois seguem para `auditoria.mensagem`, na linha do agente.
    resultado: str = "sucesso"
    modelo: str = ""


class AnswerChatMessage:
    def __init__(self, model: ChatModel) -> None:
        self._model = model

    def answer(self, message: str, conversation_id: str | None = None) -> ChatReply:
        trimmed = message.strip()
        if not trimmed:
            raise ChatReceptionError(ChatReceptionErrorCode.EMPTY_MESSAGE)
        if len(trimmed) > MAX_MESSAGE_LENGTH:
            raise ChatReceptionError(ChatReceptionErrorCode.MESSAGE_TOO_LONG)

        try:
            resposta = self._model.generate_reply(trimmed, conversation_id=conversation_id)
            return ChatReply(
                text=resposta.texto,
                fontes=tuple(resposta.fontes),
                resultado=resposta.resultado,
                modelo=resposta.modelo,
            )
        except ChatModelUnavailableError as exc:
            raise ChatReceptionError(ChatReceptionErrorCode.SERVICE_UNAVAILABLE) from exc
