from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_chat_answerer
from az1_api.main import app
from services.chat_service import ChatReceptionError, ChatReceptionErrorCode, ChatReply


class FakeAnswerer:
    def __init__(self, result: ChatReply | Exception) -> None:
        self.result = result

    def answer(self, message: str) -> ChatReply:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class TestChatAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: ChatReply | Exception) -> TestClient:
        app.dependency_overrides[get_chat_answerer] = lambda: FakeAnswerer(result)
        return TestClient(app, raise_server_exceptions=False)

    def test_responde_mensagem_com_sucesso(self) -> None:
        client = self._client_with(ChatReply(text="Olá! Como posso ajudar?"))

        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "conversation_id": "conv_123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "Olá! Como posso ajudar?"})

    def test_retorna_422_quando_campo_message_esta_ausente(self) -> None:
        client = self._client_with(ChatReply(text="não utilizado"))

        response = client.post("/api/v1/chat", json={"conversation_id": "conv_123"})

        self.assertEqual(response.status_code, 422)

    def test_mapeia_erros_controlados(self) -> None:
        cases = (
            (ChatReceptionErrorCode.EMPTY_MESSAGE, 422, "empty_message"),
            (ChatReceptionErrorCode.MESSAGE_TOO_LONG, 422, "message_too_long"),
            (ChatReceptionErrorCode.SERVICE_UNAVAILABLE, 503, "service_unavailable"),
        )
        for code, status, error in cases:
            with self.subTest(code=code):
                client = self._client_with(ChatReceptionError(code))
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Oi", "conversation_id": "conv_123"},
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"], error)

    def test_oculta_detalhes_de_erro_inesperado(self) -> None:
        client = self._client_with(RuntimeError("segredo interno"))

        with self.assertLogs("az1_api.main", level="ERROR"):
            response = client.post(
                "/api/v1/chat",
                json={"message": "Oi", "conversation_id": "conv_123"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"error": "internal_error", "message": "Erro interno inesperado."},
        )
        self.assertNotIn("segredo interno", response.text)


if __name__ == "__main__":
    unittest.main()
