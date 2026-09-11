from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_chat_answerer, require_authenticated_user
from az1_api.main import app
from rag.retriever import ResultadoBusca
from routes.chat import fontes_citadas, limpar_citacoes
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


class TesteFontesCitadas(unittest.TestCase):
    """Só o que a resposta citou vira fonte, com a numeração do texto."""

    @staticmethod
    def _fonte(projeto: str, arquivo: str) -> ResultadoBusca:
        return ResultadoBusca(
            texto=f"trecho de {projeto}",
            score=0.7,
            projeto_id=projeto,
            tipo_documento="riscos_problemas",
            secao="Riscos",
            arquivo_origem=arquivo,
            chunk_id=f"id-{projeto}",
        )

    def setUp(self):
        self.recuperadas = [
            self._fonte("SYN-01", "03_Mapa.xlsx"),
            self._fonte("SYN-01", "01_Termo.docx"),
            self._fonte("SYN-01", "04_Riscos.xlsx"),
            self._fonte("SYN-01", "01_Termo.docx"),
            self._fonte("SYN-02", "04_Riscos.xlsx"),
        ]

    def test_devolve_apenas_as_citadas(self):
        # A busca entrega cinco ao modelo e ele costuma usar dois. Listar os
        # cinco faria o usuário abrir documento que não sustenta nada.
        fontes = fontes_citadas("Os riscos são A [3] e B [3].", self.recuperadas)
        self.assertEqual([f.posicao for f in fontes], [3])

    def test_entende_citacao_com_varios_numeros(self):
        # O modelo escreve "[3, 4]" quando a afirmação vem de dois trechos.
        fontes = fontes_citadas("Risco A [3, 4] e risco B [5].", self.recuperadas)
        self.assertEqual([f.posicao for f in fontes], [3, 4, 5])

    def test_preserva_a_numeracao_do_texto(self):
        # Renumerar para 1,2 quebraria a ligação com o "[3]" escrito na
        # resposta, que é o que torna a citação conferível.
        fontes = fontes_citadas("Apenas isto [4].", self.recuperadas)
        self.assertEqual(fontes[0].posicao, 4)
        self.assertEqual(fontes[0].arquivo_origem, "01_Termo.docx")

    def test_sem_citacao_devolve_lista_vazia(self):
        self.assertEqual(fontes_citadas("Resposta sem citar nada.", self.recuperadas), [])

    def test_numero_fora_da_faixa_e_ignorado(self):
        # Modelo alucinando "[9]" não pode virar fonte inexistente na resposta.
        fontes = fontes_citadas("Veja [9] e [2].", self.recuperadas)
        self.assertEqual([f.posicao for f in fontes], [2])

    def test_o_projeto_acompanha_a_fonte(self):
        # Todo projeto tem um 04_Riscos.xlsx: sem o código do projeto, duas
        # fontes distintas parecem a mesma na interface.
        fontes = fontes_citadas("A [3] e B [5].", self.recuperadas)
        self.assertEqual([f.projeto_id for f in fontes], ["SYN-01", "SYN-02"])


class TesteLimpezaDasCitacoes(unittest.TestCase):
    """Os marcadores somem do texto, mas depois de terem feito o trabalho."""

    def test_remove_citacao_simples_sem_deixar_espaco(self):
        self.assertEqual(
            limpar_citacoes("O risco e critico [3]."),
            "O risco e critico.",
        )

    def test_remove_citacao_com_varios_numeros(self):
        self.assertEqual(
            limpar_citacoes("Atraso na entrega [3, 4], e adequacoes eletricas [3,4]."),
            "Atraso na entrega, e adequacoes eletricas.",
        )

    def test_texto_sem_citacao_fica_intacto(self):
        original = "Nao encontrei essa informacao nos documentos."
        self.assertEqual(limpar_citacoes(original), original)

    def test_nao_come_colchete_que_nao_e_citacao(self):
        # "[R01]" e identificador de risco nos documentos, nao referencia.
        self.assertEqual(limpar_citacoes("Ver o risco [R01]."), "Ver o risco [R01].")

    def test_a_fonte_e_extraida_antes_da_limpeza(self):
        # A ordem e o ponto: limpar primeiro apagaria o sinal de quais trechos
        # o modelo usou, e a lista de fontes voltaria a ser os cinco
        # recuperados em vez dos dois citados.
        recuperadas = [
            ResultadoBusca(
                texto=f"trecho {n}", score=0.7, projeto_id="SYN-01",
                tipo_documento="riscos_problemas", secao="", arquivo_origem=f"{n}.xlsx",
                chunk_id=str(n),
            )
            for n in range(1, 4)
        ]
        bruto = "Risco A [2]."
        fontes = fontes_citadas(bruto, recuperadas)
        limpo = limpar_citacoes(bruto)

        self.assertEqual([f.posicao for f in fontes], [2])
        self.assertEqual(limpo, "Risco A.")
        self.assertEqual(fontes_citadas(limpo, recuperadas), [])


if __name__ == "__main__":
    unittest.main()
