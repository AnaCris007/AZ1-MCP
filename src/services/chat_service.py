from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

MAX_MESSAGE_LENGTH = 4000


class ChatModel(Protocol):
    def generate_reply(self, message: str) -> str: ...


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


class AnswerChatMessage:
    def __init__(self, model: ChatModel) -> None:
        self._model = model

    def answer(self, message: str) -> ChatReply:
        trimmed = message.strip()
        if not trimmed:
            raise ChatReceptionError(ChatReceptionErrorCode.EMPTY_MESSAGE)
        if len(trimmed) > MAX_MESSAGE_LENGTH:
            raise ChatReceptionError(ChatReceptionErrorCode.MESSAGE_TOO_LONG)

        try:
            return ChatReply(text=self._model.generate_reply(trimmed))
        except ChatModelUnavailableError as exc:
            raise ChatReceptionError(ChatReceptionErrorCode.SERVICE_UNAVAILABLE) from exc
