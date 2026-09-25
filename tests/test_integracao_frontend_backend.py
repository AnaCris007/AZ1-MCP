"""Frontend e backend — casos TI-30 a TI-34 (Seção 6.4.4).

Esta suíte verifica o CONTRATO entre a interface e a aplicação, e o limite do
instrumento precisa ficar dito logo: `TestClient` não executa React. O que se
pode afirmar daqui é que o backend aceita exatamente o que o cliente envia e
devolve exatamente o que o cliente espera desserializar. O comportamento da
interface diante de cada resposta é evidência de componente, e mora na suíte
Vitest de `src/frontend` (`npm test`), citada caso a caso.

**TI-33 trocou de massa, não de invariante.** O planejamento listava
`GET /api/v1/tasks`, `PATCH /api/v1/tasks/{id}` e `GET /api/v1/calendar/events`
como as três rotas ausentes da época; as três foram implementadas desde então em
`src/routes/portfolio.py`. O que o caso afirma, porém, nunca foi sobre essas
rotas em particular: é que **uma rota não implementada responde `404` limpo**, e
isso continua valendo e continua precisando de teste — a interface chama
endereços, e precisa distinguir "não existe" de "quebrou". O caso mantém o nome
planejado e passa a exercitar a invariante contra rotas que de fato não existem;
um caso irmão registra que as três da massa original hoje existem.

Execução:

    python -m unittest tests.test_integracao_frontend_backend -v
"""

from __future__ import annotations

import io
import re
import unittest
import uuid
import wave
from types import SimpleNamespace

from az1_api.dependencies import (
    get_agente,
    get_audio_receiver,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    get_evento_local_repository,
    get_portfolio_repository,
)
from az1_api.main import app
from services.agente_service import AgenteDesligado
from services.audio_service import AudioReceipt
from services.chat_service import AnswerChatMessage
from services.conversa_repository import PersistenciaDesligada
from tests.apoio_integracao import RAIZ, cliente, limpar_overrides

VITE_CONFIG = RAIZ / "src" / "frontend" / "vite.config.js"
COMPOSE_OVERRIDE = RAIZ / "docker-compose.override.yml"

# As três rotas que o planejamento listava como ausentes e que hoje existem.
# O terceiro elemento é o caminho como o roteador o declara, com o parâmetro
# entre chaves — é assim que ele aparece no esquema OpenAPI.
ROTAS_DE_PORTFOLIO = (
    ("GET", "/api/v1/tasks", "/api/v1/tasks"),
    ("PATCH", "/api/v1/tasks/1", "/api/v1/tasks/{pendencia_id}"),
    ("GET", "/api/v1/calendar/events", "/api/v1/calendar/events"),
)


def _wav_valido(segundos: float = 0.4) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as saida:
        saida.setnchannels(1)
        saida.setsampwidth(2)
        saida.setframerate(24_000)
        saida.writeframes(b"\x00\x01" * int(24_000 * segundos))
    return buffer.getvalue()


class _RecebedorFixo:
    def __init__(self) -> None:
        self.recebidos = 0

    def receive(self, content) -> AudioReceipt:
        self.recebidos += 1
        return AudioReceipt(audio_id="aud_contrato")


class _ModeloFixo:
    """Implementa o `ChatModel`, e não o `AnswerChatMessage`.

    A diferença importa: é `AnswerChatMessage` que recusa mensagem vazia e
    mensagem longa demais. Substituí-lo por um dublê apagaria essa validação, e
    TI-32 passaria a afirmar que `/chat` aceita string em branco — que é o
    oposto do contrato. Dublando só o MODELO, a pilha de validação continua
    sendo a de produção.
    """

    def __init__(self, texto: str = "Resposta do agente.") -> None:
        self._texto = texto
        self.mensagens: list[str] = []

    def generate_reply(self, message: str, *, conversation_id: str | None = None, **_):
        self.mensagens.append(message)
        return SimpleNamespace(texto=self._texto, fontes=(), resultado="sucesso", modelo="duble")


def _respondedor(texto: str = "Resposta do agente.") -> AnswerChatMessage:
    return AnswerChatMessage(_ModeloFixo(texto))


class _PortfolioVazio:
    """Repositório sem banco, para verificar a FORMA das rotas de portfólio.

    O conteúdo delas depende do PostgreSQL e é verificado em TI-24 a TI-29. O
    que TI-33 precisa é saber se a rota existe e qual o contrato — e para isso
    um repositório que devolve listas vazias basta e não arrasta o banco.
    """

    def situacao_dos_projetos(self) -> list:
        return []

    def pendencias(self) -> list:
        return []

    def alterar_situacao(self, *, pendencia_id: int, situacao: str):
        return None


class _EventosLocaisVazios:
    """Repositório sem banco para a parcela local da Agenda."""

    def listar(self, usuario_id: int) -> tuple:
        return ()


class TestFrontendBackendIntegracao(unittest.TestCase):
    """TI-30 a TI-34."""

    def tearDown(self) -> None:
        limpar_overrides()

    # -- TI-30 ---------------------------------------------------------------

    def test_contrato_da_rota_de_chat(self) -> None:
        """Os campos de `ChatRequest`/`ChatResponse` valem nos dois sentidos.

        Evidência de componente correspondente: `src/frontend/src/lib/api.test.js`.
        """
        modelo = _ModeloFixo()
        answer = AnswerChatMessage(modelo)
        http = cliente(
            {
                get_chat_answerer: lambda: answer,
                get_conversa_repository: lambda: PersistenciaDesligada("teste"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("teste"),
            }
        )

        conversa = str(uuid.uuid4())
        resposta = http.post(
            "/api/v1/chat", json={"message": "Como está a linha 6?", "conversation_id": conversa}
        )

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        # Ida: a mensagem chegou íntegra ao serviço.
        self.assertEqual(modelo.mensagens, ["Como está a linha 6?"])
        # Volta: exatamente os campos que o cliente desserializa.
        self.assertEqual(set(corpo), {"reply", "fontes"})
        self.assertIsInstance(corpo["reply"], str)
        self.assertIsInstance(corpo["fontes"], list)

    def test_conversation_id_e_obrigatorio_no_contrato_de_chat(self) -> None:
        """Faltando `conversation_id`, o backend recusa com 422.

        Complementa TI-30 pelo lado negativo: o campo é obrigatório em
        `ChatRequest`, e um cliente que o omitisse não receberia 200 silencioso.
        """
        http = cliente(
            {
                get_chat_answerer: _respondedor,
                get_conversa_repository: lambda: PersistenciaDesligada("teste"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("teste"),
            }
        )

        resposta = http.post("/api/v1/chat", json={"message": "sem conversa"})

        self.assertEqual(resposta.status_code, 422)

    # -- TI-31 ---------------------------------------------------------------

    def test_contrato_do_envio_de_audio(self) -> None:
        """`Blob` sem nome de arquivo, como o `MediaRecorder` do navegador manda.

        O navegador anexa o áudio gravado sem `filename`. Se a rota dependesse
        dele, a gravação funcionaria no `curl` da documentação e falharia na
        interface — e é por isso que o caso envia o campo do jeito ruim de
        propósito.
        """
        recebedor = _RecebedorFixo()
        http = cliente({get_audio_receiver: lambda: recebedor})

        # `formData.append('audio', blob)` em `src/frontend/src/lib/api.js`:
        # anexar um Blob que não é File faz o navegador enviar a parte com
        # `filename="blob"` — sem extensão e sem relação com o formato real.
        resposta = http.post(
            "/api/v1/audio",
            files={"audio": ("blob", _wav_valido(), "audio/wav")},
        )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(set(resposta.json()), {"id", "status", "message"})
        self.assertEqual(resposta.json()["status"], "received")
        self.assertEqual(recebedor.recebidos, 1)

        # Caracterização da fronteira literal da ficha do caso ("sem nome de
        # arquivo"): uma parte multipart SEM `filename` algum não é tratada como
        # arquivo pelo Starlette, e a rota recusa com 422. Nenhum navegador
        # produz essa requisição por `FormData.append` — o registro existe para
        # que a diferença entre "sem extensão" e "sem filename" fique explícita,
        # e não para aprovar ou reprovar o comportamento.
        sem_filename = http.post("/api/v1/audio", files={"audio": ("", _wav_valido(), "audio/wav")})
        self.assertEqual(sem_filename.status_code, 422)
        self.assertEqual(recebedor.recebidos, 1, "a recusa acontece antes do serviço")

    # -- TI-32 ---------------------------------------------------------------

    def test_erro_4xx_5xx_e_tratado_pela_interface(self) -> None:
        """O envelope de erro é sempre o mesmo, e é o que a interface lê.

        O que se verifica AQUI é o lado do backend: `4xx` e `5xx` das rotas de
        negócio saem com `{error, message}`, e não com formatos diferentes por
        rota — um cliente que lê `corpo.message` funciona para todos.

        O que se verifica na interface está em
        `src/frontend/src/pages/AgentPage.test.jsx`, que cobre a exibição do
        estado de falha sem travar a tela. Este caso não afirma nada sobre React.
        """
        http = cliente(
            {
                get_chat_answerer: _respondedor,
                get_conversa_repository: lambda: PersistenciaDesligada("teste"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("teste"),
            }
        )

        # 422 do serviço de chat.
        vazia = http.post(
            "/api/v1/chat", json={"message": "   ", "conversation_id": str(uuid.uuid4())}
        )
        self.assertEqual(vazia.status_code, 422)
        self.assertEqual(set(vazia.json()), {"error", "message"})

        # 404 do serviço de transcrição, com o mesmo envelope.
        from az1_api.dependencies import get_transcriber
        from services.transcription_service import TranscriptionError, TranscriptionErrorCode

        class _TranscritorAusente:
            async def transcribe(self, *, audio_id: str, language: str = "pt-BR"):
                raise TranscriptionError(TranscriptionErrorCode.AUDIO_NOT_FOUND)

        http2 = cliente({get_transcriber: lambda: _TranscritorAusente()})
        ausente = http2.post("/api/v1/audio/aud_qualquer/transcribe")
        self.assertEqual(ausente.status_code, 404)
        self.assertEqual(set(ausente.json()), {"error", "message"})

        # E as mensagens são legíveis por pessoa, não despejos técnicos.
        for resposta in (vazia, ausente):
            mensagem = resposta.json()["message"]
            self.assertTrue(mensagem.strip())
            self.assertNotIn("Traceback", mensagem)

    # -- TI-33 ---------------------------------------------------------------

    def test_rotas_nao_implementadas_retornam_404(self) -> None:
        """Rota que não existe responde `404` limpo, e não 500 nem 405.

        **A invariante do caso é essa, e ela não envelheceu.** O planejamento
        listava `GET /api/v1/tasks`, `PATCH /api/v1/tasks/{id}` e
        `GET /api/v1/calendar/events` como as três rotas ausentes da época —
        eram a massa disponível, não o objeto do teste. As três foram
        implementadas desde então (ver o caso seguinte), e o que continua
        valendo é o contrato que protege a interface: quando o cliente chama um
        endereço que o backend não serve, a resposta é `404`, com o envelope
        `{"detail": ...}` do próprio framework.

        A distinção com o `{error, message}` das rotas de negócio é o que
        permite à interface separar "o recurso que você pediu não existe" de
        "esse endereço não é servido por este backend" — a primeira é dado, a
        segunda é defeito de integração ou versão errada do cliente.
        """
        http = cliente()

        for caminho in (
            "/api/v1/tasks/1/comentarios",
            "/api/v1/projetos/SYN-04/relatorio",
            # Evita o padrão DELETE /calendar/events/{evento_id}: nesse
            # endereço o caminho existe e um GET deve responder 405.
            "/api/v1/calendar/sem-rota",
        ):
            with self.subTest(rota=caminho):
                # Confirmado contra o roteador: se algum destes passar a
                # existir, o caso precisa de massa nova em vez de passar por
                # engano contra uma rota que agora é servida.
                self.assertNotIn(caminho, set(app.openapi()["paths"]))

                resposta = http.get(caminho)

                self.assertEqual(resposta.status_code, 404)
                self.assertIn("detail", resposta.json())
                self.assertNotIn(
                    "error",
                    resposta.json(),
                    "rota inexistente não pode usar o envelope das rotas de negócio",
                )

    def test_rotas_de_portfolio_do_planejamento_foram_implementadas(self) -> None:
        """Complemento de TI-33: as três rotas da massa original hoje existem.

        Este caso é o registro da mudança. `src/routes/portfolio.py` implementou
        as três desde a escrita do planejamento, e o que se verifica agora é que
        respeitam o contrato que a interface consome — e, principalmente, que o
        `404` que o `PATCH` devolve é de RECURSO, com envelope de negócio, e não
        o `404` de rota inexistente do caso acima. Confundir os dois é o erro
        que o par de casos existe para tornar impossível.
        """
        http = cliente(
            {
                get_portfolio_repository: _PortfolioVazio,
                get_evento_local_repository: _EventosLocaisVazios,
            }
        )
        caminhos = set(app.openapi()["paths"])

        for metodo, caminho, modelo in ROTAS_DE_PORTFOLIO:
            with self.subTest(rota=f"{metodo} {caminho}"):
                self.assertIn(modelo, caminhos, "a rota saiu do roteador; atualize o caso")

        listagem = http.get("/api/v1/tasks")
        self.assertEqual(listagem.status_code, 200)
        self.assertEqual(listagem.json(), [])

        agenda = http.get("/api/v1/calendar/events")
        self.assertEqual(agenda.status_code, 200)
        self.assertIn("days", agenda.json())

        alteracao = http.patch("/api/v1/tasks/1", json={"done": True})
        self.assertEqual(alteracao.status_code, 404)
        self.assertEqual(
            alteracao.json()["error"],
            "pendencia_nao_encontrada",
            "404 de recurso usa o envelope de negócio; o de rota inexistente não",
        )

    # -- TI-34 ---------------------------------------------------------------

    def test_porta_do_proxy_coincide_com_a_porta_do_servidor(self) -> None:
        """O alvo padrão do proxy do Vite é a porta que o compose publica.

        Duas declarações em arquivos diferentes que precisam concordar; quando
        divergem, o sintoma é a interface subir e toda chamada de API falhar
        com 500 do proxy — sem nenhum erro no backend, porque ele nem foi
        procurado.
        """
        config = VITE_CONFIG.read_text(encoding="utf-8")
        alvo = re.search(r"VITE_DEV_API_PROXY\s*\?\?\s*'http://127\.0\.0\.1:(\d+)'", config)
        self.assertIsNotNone(alvo, "não encontrei o alvo padrão do proxy em vite.config.js")
        porta_do_proxy = int(alvo.group(1))

        # Lido por expressão regular, e não por `yaml.safe_load`: o arquivo usa
        # a tag `!override` do Docker Compose, que não é YAML padrão e faz o
        # carregador seguro recusar o documento inteiro.
        compose = COMPOSE_OVERRIDE.read_text(encoding="utf-8")
        publicada = re.search(r"AZ1_API_PORT:-(\d+)", compose)
        self.assertIsNotNone(publicada, "não encontrei a porta publicada do serviço api")
        porta_publicada = int(publicada.group(1))

        self.assertEqual(
            porta_do_proxy,
            porta_publicada,
            f"o proxy do Vite aponta para {porta_do_proxy} e o compose publica {porta_publicada}",
        )

    def test_prefixo_do_proxy_cobre_as_rotas_da_api(self) -> None:
        """O proxy intercepta `/api`, e as rotas de negócio vivem sob `/api/v1`.

        Complementa TI-34: portas coincidentes não bastam se o prefixo
        interceptado não cobrir o caminho que a interface chama.
        """
        config = VITE_CONFIG.read_text(encoding="utf-8")
        self.assertIn("'/api'", config)

        http = cliente(
            {
                get_chat_answerer: _respondedor,
                get_conversa_repository: lambda: PersistenciaDesligada("teste"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("teste"),
            }
        )
        resposta = http.post(
            "/api/v1/chat", json={"message": "oi", "conversation_id": str(uuid.uuid4())}
        )
        self.assertEqual(resposta.status_code, 200)


if __name__ == "__main__":
    unittest.main()
