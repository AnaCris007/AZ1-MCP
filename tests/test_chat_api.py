from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_chat_answerer, require_authenticated_user
from az1_api.main import app
from rag.retriever import ResultadoBusca
from services.auth_service import AuthenticatedUser
from services.chat_service import ChatReceptionError, ChatReceptionErrorCode, ChatReply


class FakeAnswerer:
    def __init__(self, result: ChatReply | Exception) -> None:
        self.result = result

    def answer(self, message: str, conversation_id: str | None = None) -> ChatReply:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


_TEST_USER = AuthenticatedUser(subject="test-user", email="teste@example.com", name="Usuário de Teste", provider="azure")


class TestChatAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: ChatReply | Exception) -> TestClient:
        app.dependency_overrides[get_chat_answerer] = lambda: FakeAnswerer(result)
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        return TestClient(app, raise_server_exceptions=False)

    def test_responde_mensagem_com_sucesso(self) -> None:
        client = self._client_with(ChatReply(text="Olá! Como posso ajudar?"))

        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "conversation_id": "conv_123"},
        )

        self.assertEqual(response.status_code, 200)
        # `fontes` entrou no contrato para que a resposta possa citar de onde
        # veio (RNF12). Vazia aqui porque este dublê não devolve fonte alguma.
        self.assertEqual(response.json(), {"reply": "Olá! Como posso ajudar?", "fontes": []})

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


class TestChatAPIFontes(unittest.TestCase):
    """A citação só é verificável se a fonte chegar ao cliente."""

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_fontes_chegam_numeradas_a_partir_de_um(self) -> None:
        fonte = ResultadoBusca(
            texto="O marco foi replanejado para outubro.",
            score=0.87,
            projeto_id="SYN-04",
            tipo_documento="cronograma",
            secao="Marcos",
            arquivo_origem="02_Cronograma.xlsx",
            chunk_id="9f2b1c7d",
        )
        resposta = ChatReply(text="O marco foi replanejado [1].", fontes=(fonte,))
        app.dependency_overrides[get_chat_answerer] = lambda: FakeAnswerer(resposta)
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        client = TestClient(app, raise_server_exceptions=False)

        corpo = client.post(
            "/api/v1/chat", json={"message": "marcos", "conversation_id": "c1"}
        ).json()

        self.assertEqual(len(corpo["fontes"]), 1)
        # O `[1]` citado no texto tem de ser a `posicao` 1 da lista: é o que
        # liga a afirmação ao trecho, e o mesmo inteiro vai para
        # auditoria.mensagem_fonte.posicao.
        self.assertEqual(corpo["fontes"][0]["posicao"], 1)
        self.assertEqual(corpo["fontes"][0]["arquivo_origem"], "02_Cronograma.xlsx")
        self.assertEqual(corpo["fontes"][0]["chunk_id"], "9f2b1c7d")


if __name__ == "__main__":
    unittest.main()
