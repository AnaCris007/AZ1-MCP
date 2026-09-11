from __future__ import annotations

import unittest

from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    AnswerChatMessage,
    ChatModelUnavailableError,
    ChatReceptionError,
    ChatReceptionErrorCode,
)


class FakeChatModel:
    def __init__(self, reply: str = "resposta") -> None:
        self.reply = reply
        self.received_messages: list[str] = []
        self.received_conversation_ids: list[str | None] = []

    def generate_reply(self, message: str, *, conversation_id: str | None = None) -> str:
        self.received_messages.append(message)
        self.received_conversation_ids.append(conversation_id)
        return self.reply


class UnavailableChatModel:
    def generate_reply(self, message: str, *, conversation_id: str | None = None) -> str:
        raise ChatModelUnavailableError


class TestAnswerChatMessage(unittest.TestCase):
    def test_repassa_mensagem_tratada_ao_modelo(self) -> None:
        model = FakeChatModel(reply="Olá!")
        answerer = AnswerChatMessage(model=model)

        result = answerer.answer("  Oi, tudo bem?  ")

        self.assertEqual(result.text, "Olá!")
        self.assertEqual(model.received_messages, ["Oi, tudo bem?"])

    def test_rejeita_mensagem_vazia(self) -> None:
        answerer = AnswerChatMessage(model=FakeChatModel())

        with self.assertRaises(ChatReceptionError) as ctx:
            answerer.answer("   ")

        self.assertEqual(ctx.exception.code, ChatReceptionErrorCode.EMPTY_MESSAGE)

    def test_rejeita_mensagem_muito_longa(self) -> None:
        answerer = AnswerChatMessage(model=FakeChatModel())

        with self.assertRaises(ChatReceptionError) as ctx:
            answerer.answer("a" * (MAX_MESSAGE_LENGTH + 1))

        self.assertEqual(ctx.exception.code, ChatReceptionErrorCode.MESSAGE_TOO_LONG)

    def test_converte_indisponibilidade_do_modelo_em_service_unavailable(self) -> None:
        answerer = AnswerChatMessage(model=UnavailableChatModel())

        with self.assertRaises(ChatReceptionError) as ctx:
            answerer.answer("Oi")

        self.assertEqual(ctx.exception.code, ChatReceptionErrorCode.SERVICE_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
