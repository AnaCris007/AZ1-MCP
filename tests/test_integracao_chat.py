"""Chat e provedor de modelo de linguagem — casos TI-20 a TI-23 (Seção 6.4.4).

A fronteira sob teste é `AnswerChatMessage` → `GeminiChatModel` → `google-genai`.
TI-20 a atravessa com a fita gravada do provedor; TI-21 caracteriza a tradução
de cada falha em código HTTP; TI-22 e TI-23 verificam que a validação de entrada
precede a chamada, como a Seção 6.4.1 exige.

**Sobre TI-21, e por que ele é caracterização e não aprovação.** A Seção 6.4.2
descreve um contrato que não é uniforme, e o caso registra isso em vez de
maquiar: `ServerError` e `ClientError` 429 viram `503 service_unavailable`;
qualquer outra exceção escapa como `500 internal_error`; texto nulo estoura na
serialização e também dá 500; e string vazia é ACEITA pelo schema, devolvendo
`200` com `reply=""`. Esse último não é resposta útil, e o caso não o aprova —
apenas fixa qual é o comportamento de hoje, para que uma mudança apareça.

Um detalhe que o planejamento já registrava e continua valendo: o 429 do
provedor NÃO vira 429 público. Ele é traduzido em 503, porque o limite excedido
é do AZ1 contra o Google, não do usuário contra o AZ1 — devolver 429 diria à
interface que quem exagerou foi quem perguntou.

A fita foi gravada sem buscador de contexto injetado, que é o caminho
`_Situacao.SEM_BUSCA` de `gemini_service._preparar`: a pergunta vai crua ao
modelo. Montar o modelo aqui com RAG ligado mudaria o corpo da requisição e a
fita deixaria de corresponder — que é exatamente o que o `match_on` com `body`
existe para garantir.

Execução:

    python -m unittest tests.test_integracao_chat -v
"""

from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace

from google.genai import errors

from az1_api.dependencies import (
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
)
from services.agente_service import AgenteDesligado
from services.chat_service import MAX_MESSAGE_LENGTH, AnswerChatMessage
from services.conversa_repository import PersistenciaDesligada
from services.gemini_service import GeminiChatModel, GeminiSettings
from tests.apoio_integracao import (
    PERGUNTA_CHAT,
    chave_chat_da_massa,
    cliente,
    leitor_vhs,
    limpar_overrides,
    modelo_de_chat,
)


class _ClienteGenaiFalso:
    """Substitui o `genai.Client` no ponto exato em que o SDK seria acionado.

    A primeira versão desta suíte substituía o `GeminiChatModel` inteiro, e
    estava errada: é DENTRO dele que `ServerError` e `ClientError` 429 viram
    `ChatModelUnavailableError`. Um dublê no lugar do modelo pula justamente a
    tradução que TI-21 existe para verificar — e o caso passava a medir o
    `except` do teste, não o do código. Com a falha injetada aqui, o caminho
    percorrido é o de produção inteiro: SDK → `GeminiChatModel` →
    `AnswerChatMessage` → rota.

    A forma imita a do SDK (`cliente.models.generate_content(...)`), e o
    contador vive na fronteira do provedor — o que torna "não acionou o
    provedor" uma asserção literal em TI-22 e TI-23.
    """

    def __init__(self, *, texto: str | None = "resposta do provedor", erro: Exception | None = None) -> None:
        self.chamadas: list[dict] = []
        self._texto = texto
        self._erro = erro
        self.models = self

    def generate_content(self, **argumentos: object) -> SimpleNamespace:
        self.chamadas.append(argumentos)
        if self._erro is not None:
            raise self._erro
        return SimpleNamespace(text=self._texto)


class TestChatIntegracao(unittest.TestCase):
    """TI-20 a TI-23."""

    def tearDown(self) -> None:
        limpar_overrides()

    def _perguntar(self, respondedor: AnswerChatMessage, mensagem: str):
        """Envia a mensagem com tudo o que não é a fronteira do chat desligado.

        Persistência, classificador e Agente são efeitos colaterais de `/chat`
        (ver os comentários de `dependencies.py`). Cada um tem fronteira e casos
        próprios; mantê-los em pé aqui faria esta suíte falhar por banco fora do
        ar, que não é o que ela mede.
        """
        http = cliente(
            {
                get_chat_answerer: lambda: respondedor,
                get_conversa_repository: lambda: PersistenciaDesligada("desligado no ensaio"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("desligado no ensaio"),
            }
        )
        return http.post(
            "/api/v1/chat",
            json={"message": mensagem, "conversation_id": str(uuid.uuid4())},
        )

    def _com_espiao(self, mensagem: str, *, espiao: _ClienteGenaiFalso | None = None):
        """Monta a pilha real de chat sobre um cliente de SDK controlado."""
        espiao = espiao or _ClienteGenaiFalso()
        modelo = GeminiChatModel(client=espiao, model=modelo_de_chat())
        return self._perguntar(AnswerChatMessage(modelo), mensagem), espiao

    # -- TI-20 ---------------------------------------------------------------

    def test_resposta_gerada_pelo_provedor(self) -> None:
        """Mensagem típica atravessa até `reply`, com a resposta real gravada."""
        modelo = GeminiChatModel.from_settings(
            GeminiSettings(api_key="irrelevante-no-replay", model=modelo_de_chat())
        )

        with leitor_vhs().fita(chave_chat_da_massa()) as fita:
            resposta = self._perguntar(AnswerChatMessage(modelo), PERGUNTA_CHAT)

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertTrue(corpo["reply"].strip(), "a fita guarda uma resposta real; ela não pode vir vazia")
        # Sem RAG injetado não há trecho recuperado, e a lista de fontes é vazia
        # por construção — não por falha. TI-55 cobre o caminho com busca.
        self.assertEqual(corpo["fontes"], [])
        self.assertEqual(fita.play_count, 1)

    # -- TI-21 ---------------------------------------------------------------

    def test_variantes_de_falha_e_resposta_vazia(self) -> None:
        """Cada variante isolada, com o status que o contrato de hoje produz."""
        variantes = (
            (
                "ServerError do provedor",
                _ClienteGenaiFalso(erro=errors.ServerError(503, {"error": {"message": "overloaded"}})),
                503,
                "service_unavailable",
            ),
            (
                "ClientError 429 do provedor",
                _ClienteGenaiFalso(erro=errors.ClientError(429, {"error": {"message": "rate limit"}})),
                503,
                "service_unavailable",
            ),
            (
                "exceção não tratada",
                _ClienteGenaiFalso(erro=RuntimeError("falha inesperada (simulada)")),
                500,
                "internal_error",
            ),
            (
                "texto nulo do provedor",
                _ClienteGenaiFalso(texto=None),
                500,
                "internal_error",
            ),
        )

        for descricao, espiao, status, erro in variantes:
            with self.subTest(variante=descricao):
                resposta, usado = self._com_espiao(PERGUNTA_CHAT, espiao=espiao)

                self.assertEqual(resposta.status_code, status)
                self.assertEqual(resposta.json()["error"], erro)
                self.assertEqual(len(usado.chamadas), 1, "o provedor foi acionado antes de falhar")

        # A quinta variante devolve 200, e é a que o caso registra sem aprovar.
        with self.subTest(variante="texto vazio do provedor"):
            resposta, _ = self._com_espiao(
                PERGUNTA_CHAT, espiao=_ClienteGenaiFalso(texto="")
            )

            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(
                resposta.json()["reply"],
                "",
                "contrato atual: string vazia passa pelo schema. Não é resposta útil; "
                "o caso fixa o comportamento para que uma mudança apareça.",
            )

    def test_429_do_provedor_nao_vira_429_publico(self) -> None:
        """A tradução do limite excedido, separada por ser fácil de errar.

        Complementa TI-21. Repassar o 429 diria à interface que quem excedeu o
        limite foi o usuário; quem excedeu foi o AZ1 contra o Google.
        """
        resposta, _ = self._com_espiao(
            PERGUNTA_CHAT,
            espiao=_ClienteGenaiFalso(erro=errors.ClientError(429, {"error": {"message": "rate limit"}})),
        )

        self.assertNotEqual(resposta.status_code, 429)
        self.assertEqual(resposta.status_code, 503)

    # -- TI-22 ---------------------------------------------------------------

    def test_mensagem_acima_do_limite_nao_aciona_o_provedor(self) -> None:
        """Acima de 4000 caracteres, a recusa vem antes da chamada."""
        resposta, espiao = self._com_espiao("a" * (MAX_MESSAGE_LENGTH + 1))

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["error"], "message_too_long")
        self.assertEqual(espiao.chamadas, [])

    def test_mensagem_no_limite_exato_e_aceita(self) -> None:
        """A fronteira do limite: 4000 passam, 4001 não. Complementa TI-22."""
        resposta, espiao = self._com_espiao("a" * MAX_MESSAGE_LENGTH)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(espiao.chamadas), 1)

    # -- TI-23 ---------------------------------------------------------------

    def test_mensagem_vazia_nao_aciona_o_provedor(self) -> None:
        """Vazia e só-espaços param no serviço, sem chamada externa."""
        for descricao, mensagem in (("vazia", ""), ("apenas espaços", "   \t\n  ")):
            with self.subTest(mensagem=descricao):
                resposta, espiao = self._com_espiao(mensagem)

                self.assertEqual(resposta.status_code, 422)
                self.assertEqual(resposta.json()["error"], "empty_message")
                self.assertEqual(espiao.chamadas, [])


if __name__ == "__main__":
    unittest.main()
