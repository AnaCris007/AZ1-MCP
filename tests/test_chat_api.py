from __future__ import annotations

import dataclasses
import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import (
    get_agente,
    get_alerta_dispatcher,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    require_authenticated_user,
)
from az1_api.main import app
from pln.entidades import EntidadesExtraidas
from pln.intencao import IntencaoDetectada
from rag.retriever import ResultadoBusca
from routes.chat import fontes_citadas, limpar_citacoes
from services.agente_service import RespostaDoAgente, ResultadoAcao
from services.auth_service import AuthenticatedUser
from services.chat_service import (
    MAX_MESSAGE_LENGTH,
    ChatReceptionError,
    ChatReceptionErrorCode,
    ChatReply,
)
from services.conversa_repository import TurnoDoChat
from services.portfolio_repository import Pendencia


class FakeAnswerer:
    """Dublê do gerador de respostas, que CONTA quantas vezes foi chamado.

    A contagem não é detalhe de instrumentação: desde que a classificação
    passou a vir antes, "o modelo não foi consultado" virou comportamento
    exigido, e comportamento exigido precisa de asserção.
    """

    def __init__(self, result: ChatReply | Exception) -> None:
        self.result = result
        self.chamadas = 0

    def answer(self, message: str, conversation_id: str | None = None, **_) -> ChatReply:
        self.chamadas += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _detectada(prevista: str, confianca: float) -> IntencaoDetectada:
    return IntencaoDetectada(prevista=prevista, confianca=confianca)


class _DispatcherEspiao:
    def __init__(self) -> None:
        self.despachos: list[dict] = []

    def despachar(self, *, deteccao, origem, texto, projeto_id) -> None:
        self.despachos.append(
            {"deteccao": deteccao, "origem": origem, "texto": texto, "projeto_id": projeto_id}
        )


_TEST_USER = AuthenticatedUser(subject="test-user", email="teste@example.com", name="Usuário de Teste", provider="azure")


class TestChatAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: ChatReply | Exception) -> TestClient:
        app.dependency_overrides[get_chat_answerer] = lambda: FakeAnswerer(result)
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        # Sem classificador: estes testes verificam o contrato da resposta do
        # RAG, e não a decisão do Agente. Com o classificador real, "Oi" é
        # `fora_do_catalogo` com 83% de confiança e o Agente recusa antes de o
        # modelo ser chamado — comportamento correto, e ruído aqui.
        #
        # `setdefault` e não atribuição: o teste que PRECISA de classificador o
        # configura antes de pedir o cliente, e atribuir aqui o apagaria.
        app.dependency_overrides.setdefault(get_classificador_de_intencao, lambda: None)
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

    def setUp(self) -> None:
        # O que se testa é a numeração da fonte citada, não a classificação.
        app.dependency_overrides[get_classificador_de_intencao] = lambda: None

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



class _RepositorioEspiao:
    """Registra os turnos recebidos, ou levanta, conforme o caso sob teste."""

    def __init__(self, erro: Exception | None = None, dono: int | None = None) -> None:
        self.turnos: list[TurnoDoChat] = []
        self._erro = erro
        # None = conversa inexistente, que é o caso da maioria dos testes: o
        # porteiro da rota deixa passar e a gravação segue.
        self._dono = dono

    def registrar_turno(self, turno: TurnoDoChat) -> None:
        if self._erro is not None:
            raise self._erro
        self.turnos.append(turno)

    def dono_da_conversa(self, conversa_id: str) -> int | None:
        return self._dono


_UUID_VALIDO = "3f1c0c4e-0000-4000-8000-000000000001"


class TesteTrilhaDaConversa(unittest.TestCase):
    """O que a rota grava — e, principalmente, quando ela decide não gravar.

    O `TestClient` executa as tarefas de fundo de forma síncrona ao encerrar a
    requisição, então as asserções depois do `post` já enxergam o efeito.
    """

    def setUp(self) -> None:
        self.espiao = _RepositorioEspiao()
        self.usuario = dataclasses.replace(_TEST_USER, domain_user_id=7)
        self.addCleanup(app.dependency_overrides.clear)

    def _cliente(self, reply: ChatReply, usuario: AuthenticatedUser | None = None) -> TestClient:
        app.dependency_overrides[get_chat_answerer] = lambda: FakeAnswerer(reply)
        app.dependency_overrides[require_authenticated_user] = lambda: usuario or self.usuario
        app.dependency_overrides[get_conversa_repository] = lambda: self.espiao
        # Sem classificador por padrão: o que se testa aqui é a TRILHA. Os casos
        # que precisam de intenção o configuram ANTES de pedir o cliente, e o
        # `setdefault` é o que preserva essa configuração.
        app.dependency_overrides.setdefault(get_classificador_de_intencao, lambda: None)
        return TestClient(app, raise_server_exceptions=False)

    @staticmethod
    def _fonte() -> ResultadoBusca:
        return ResultadoBusca(
            texto="ID: R01 | Título: Atraso na entrega",
            score=0.71,
            projeto_id="SYN-01",
            tipo_documento="riscos_problemas",
            secao="Riscos",
            arquivo_origem="04_Riscos_e_Problemas.xlsx",
            chunk_id="abc123",
        )

    def test_conversa_de_outro_usuario_e_recusada(self) -> None:
        """A do vizinho não se abre, nem para ler nem para escrever.

        O `conversation_id` vem do corpo da requisição — `crypto.randomUUID()`
        no navegador —, então é entrada do usuário. Antes desta verificação,
        enviar o UUID da conversa alheia fazia `_historico_do_banco` carregar os
        turnos dela para o contexto do modelo, de onde podiam sair na resposta,
        e ainda anexava o turno novo àquela conversa.

        A recusa precisa vir ANTES de `answer()`: depois, o histórico já teria
        sido lido.
        """
        self.espiao = _RepositorioEspiao(dono=99)
        cliente = self._cliente(ChatReply(text="Resposta.", modelo="gemini-3.5-flash-lite"))

        resposta = cliente.post(
            "/api/v1/chat", json={"message": "oi", "conversation_id": _UUID_VALIDO}
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.json()["error"], "forbidden")
        self.assertEqual(self.espiao.turnos, [])

    def test_conversa_propria_continua_passando(self) -> None:
        """A verificação não pode barrar a segunda mensagem da própria conversa."""
        self.espiao = _RepositorioEspiao(dono=7)
        cliente = self._cliente(ChatReply(text="Resposta.", modelo="gemini-3.5-flash-lite"))

        resposta = cliente.post(
            "/api/v1/chat", json={"message": "oi", "conversation_id": _UUID_VALIDO}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(self.espiao.turnos), 1)

    def test_grava_com_a_identidade_autenticada(self) -> None:
        # O `usuario_id` vem de `domain_user_id`, e não de um literal. Foi um
        # literal — o zero — que produziu 9 conversas atribuídas a um id que não
        # existe em banco algum criado pelo DDL.
        cliente = self._cliente(ChatReply(text="Resposta.", modelo="gemini-3.5-flash-lite"))

        resposta = cliente.post(
            "/api/v1/chat", json={"message": "oi", "conversation_id": _UUID_VALIDO}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(self.espiao.turnos), 1)
        turno = self.espiao.turnos[0]
        self.assertEqual(turno.usuario_id, 7)
        self.assertEqual(turno.conversa_id, _UUID_VALIDO)
        self.assertEqual(turno.modelo, "gemini-3.5-flash-lite")
        self.assertGreaterEqual(turno.tempo_processamento_ms, 0)

    def test_sem_identidade_nao_grava_e_ainda_responde(self) -> None:
        # `domain_user_id` é None com AZ1_AUTH_MODE=disabled e quando o resolver
        # falhou. Inventar um id para preencher a coluna NOT NULL seria repetir
        # exatamente o defeito do `usuario_id = 0`.
        sem_identidade = dataclasses.replace(_TEST_USER, domain_user_id=None)
        cliente = self._cliente(ChatReply(text="Resposta."), usuario=sem_identidade)

        with self.assertLogs("routes.chat", level="WARNING"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "oi", "conversation_id": _UUID_VALIDO}
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.espiao.turnos, [])

    def test_conversation_id_nao_uuid_nao_custa_a_resposta(self) -> None:
        # `auditoria.conversa.id` é UUID. Recusar a requisição com 422 faria a
        # trilha — que é acessório — derrubar a conversa.
        cliente = self._cliente(ChatReply(text="Resposta."))

        with self.assertLogs("routes.chat", level="WARNING"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "oi", "conversation_id": "conv_123"}
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["reply"], "Resposta.")
        self.assertEqual(self.espiao.turnos, [])

    def test_falha_ao_gravar_nao_escapa_da_tarefa_de_fundo(self) -> None:
        # Tarefa de fundo roda depois de a resposta ter sido enviada: uma exceção
        # ali não vira resposta de erro, vira traceback solto na pilha ASGI.
        self.espiao = _RepositorioEspiao(erro=OSError("banco fora"))
        cliente = self._cliente(ChatReply(text="Resposta."))

        with self.assertLogs("routes.chat", level="ERROR"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "oi", "conversation_id": _UUID_VALIDO}
            )

        self.assertEqual(resposta.status_code, 200)

    def test_resultado_recusada_chega_a_trilha(self) -> None:
        # Gravado como 'sucesso' literal, como era antes, o relatório não
        # consegue distinguir resposta fundamentada de recusa.
        cliente = self._cliente(ChatReply(text="Não encontrei.", resultado="recusada"))

        cliente.post("/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO})

        self.assertEqual(self.espiao.turnos[0].resultado, "recusada")

    def test_posicao_gravada_e_o_numero_citado_no_texto(self) -> None:
        # É o elo do RNF12: o `[2]` que a resposta escreveu tem de ser o mesmo
        # inteiro em `mensagem_fonte.posicao`. Renumerar quebra a conferência.
        reply = ChatReply(
            text="Uma afirmação [2].",
            fontes=(self._fonte(), self._fonte()),
        )
        cliente = self._cliente(reply)

        corpo = cliente.post(
            "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
        ).json()

        gravadas = self.espiao.turnos[0].fontes
        self.assertEqual([f.posicao for f in gravadas], [2])
        self.assertEqual([f["posicao"] for f in corpo["fontes"]], [2])
        self.assertEqual(gravadas[0].chunk_id, "abc123")

    def test_intencao_observada_vai_para_a_trilha(self) -> None:
        # A trilha grava a previsão CRUA, e não o que sobra da rejeição: 0,42
        # está abaixo do limiar, o Agente não agiu, e ainda assim `orientar_tap`
        # é o que fica registrado. A regra é reconstituível a partir da
        # confiança; o argmax descartado não seria — e é dele que depende
        # recalibrar o limiar sobre tráfego real.
        app.dependency_overrides[get_classificador_de_intencao] = lambda: (
            lambda texto: _detectada("orientar_tap", 0.42)
        )
        cliente = self._cliente(ChatReply(text="Resposta."))

        cliente.post("/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO})

        turno = self.espiao.turnos[0]
        self.assertEqual(turno.intencao, "orientar_tap")
        self.assertAlmostEqual(turno.confianca_intencao, 0.42)

    def test_classificador_ausente_nao_impede_a_gravacao(self) -> None:
        # Instalação sem o `.joblib` treinado continua conversando e auditando,
        # apenas sem registrar a intenção.
        app.dependency_overrides[get_classificador_de_intencao] = lambda: None
        cliente = self._cliente(ChatReply(text="Resposta."))

        cliente.post("/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO})

        self.assertIsNone(self.espiao.turnos[0].intencao)

    def test_classificador_com_defeito_nao_derruba_a_conversa(self) -> None:
        # Classificar é acessório. Um modelo quebrado não pode custar a resposta.
        def explodir(texto):
            raise RuntimeError("modelo corrompido")

        app.dependency_overrides[get_classificador_de_intencao] = lambda: explodir
        cliente = self._cliente(ChatReply(text="Resposta."))

        with self.assertLogs("routes.chat", level="ERROR"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(self.espiao.turnos[0].intencao)


class FakeAgente:
    def __init__(self, resposta: RespostaDoAgente | Exception) -> None:
        self._resposta = resposta

    def executar(self, *, deteccao: IntencaoDetectada, texto: str) -> RespostaDoAgente:
        if isinstance(self._resposta, Exception):
            raise self._resposta
        return self._resposta


class TesteAgenteNoChat(unittest.TestCase):
    """A intenção classificada passa a poder AGIR, não só ser observada.

    `FakeAgente` substitui o Agente real: o que se testa aqui é a decisão da
    rota (sobrepor a resposta ou não, o que grava na trilha), não a lógica de
    `ExecutarIntencao` em si — essa tem sua própria suíte em
    `test_agente_service.py`.
    """

    def setUp(self) -> None:
        self.espiao = _RepositorioEspiao()
        self.usuario = dataclasses.replace(_TEST_USER, domain_user_id=7)
        self.addCleanup(app.dependency_overrides.clear)

    def _cliente(
        self,
        reply: ChatReply,
        resposta_do_agente: RespostaDoAgente | Exception,
        *,
        confianca: float = 0.9,
    ) -> TestClient:
        self.answerer = FakeAnswerer(reply)
        self.dispatcher = _DispatcherEspiao()
        app.dependency_overrides[get_chat_answerer] = lambda: self.answerer
        app.dependency_overrides[require_authenticated_user] = lambda: self.usuario
        app.dependency_overrides[get_conversa_repository] = lambda: self.espiao
        app.dependency_overrides[get_classificador_de_intencao] = lambda: (
            lambda texto: _detectada("gerar_alertas_pendencias", confianca)
        )
        app.dependency_overrides[get_agente] = lambda: FakeAgente(resposta_do_agente)
        app.dependency_overrides[get_alerta_dispatcher] = lambda: self.dispatcher
        return TestClient(app, raise_server_exceptions=False)

    def test_acao_confiante_sobrepoe_a_resposta_do_rag(self) -> None:
        pendencia = Pendencia(
            id=1, projeto_codigo="SYN-01", projeto_nome="Projeto", codigo=None,
            tipo="risco", titulo="Licença ambiental vencendo", descricao=None,
            criticidade=None, responsavel=None, prazo=None, situacao="aberta",
        )
        resposta_do_agente = RespostaDoAgente(
            ResultadoAcao.PENDENCIAS, EntidadesExtraidas(), pendencias=(pendencia,)
        )
        cliente = self._cliente(ChatReply(text="resposta do RAG, ignorada"), resposta_do_agente)

        corpo = cliente.post(
            "/api/v1/chat", json={"message": "o que precisa da minha atenção?", "conversation_id": _UUID_VALIDO}
        ).json()

        self.assertIn("Licença ambiental vencendo", corpo["reply"])
        self.assertEqual(corpo["fontes"], [])
        self.assertEqual(self.espiao.turnos[0].resultado, "sucesso")

    def test_sem_acao_mantem_a_resposta_do_rag(self) -> None:
        resposta_do_agente = RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas())
        cliente = self._cliente(ChatReply(text="Resposta do RAG."), resposta_do_agente)

        corpo = cliente.post(
            "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
        ).json()

        self.assertEqual(corpo["reply"], "Resposta do RAG.")

    def test_recusa_fora_do_catalogo_grava_resultado_recusada(self) -> None:
        resposta_do_agente = RespostaDoAgente(ResultadoAcao.RECUSADA_FORA_DO_CATALOGO, EntidadesExtraidas())
        cliente = self._cliente(ChatReply(text="resposta do RAG, ignorada"), resposta_do_agente)

        cliente.post("/api/v1/chat", json={"message": "qual a previsão do tempo?", "conversation_id": _UUID_VALIDO})

        turno = self.espiao.turnos[0]
        self.assertEqual(turno.resultado, "recusada")
        self.assertIsNone(turno.modelo)

    def test_falha_no_agente_nao_derruba_a_conversa(self) -> None:
        cliente = self._cliente(ChatReply(text="Resposta do RAG."), RuntimeError("agente quebrado"))

        with self.assertLogs("routes.chat", level="ERROR"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["reply"], "Resposta do RAG.")

class TesteClassificaAntesDeConsultarAsFontes(unittest.TestCase):
    """A ordem do handler, que por muito tempo foi o oposto do artefato.

    O handler chamava `answerer.answer` PRIMEIRO e classificava depois. Todo
    turno em que o Agente agia — pendências, situação de projeto ou recusa —
    pagava uma geração no Gemini e uma busca vetorial cujo resultado era
    descartado na linha seguinte.

    No caso da recusa isso não era só desperdício. A Seção 2.1 do Projeto.md
    especifica recusar pedidos fora do escopo "antes mesmo de consultar as
    fontes de dados", e o caso crítico 1 da Seção 2.2.3 modela a classificação
    antes do roteamento. Consultar as fontes para depois jogar a resposta fora
    é o oposto do que o artefato descreve.

    A contagem em `FakeAnswerer.chamadas` é o que impede a ordem de voltar a
    inverter sem ninguém notar: invertê-la não muda nenhuma resposta, só o
    custo e a semântica.
    """

    def setUp(self) -> None:
        self.espiao = _RepositorioEspiao()
        self.usuario = dataclasses.replace(_TEST_USER, domain_user_id=7)
        self.addCleanup(app.dependency_overrides.clear)

    def _cliente(self, resposta_do_agente: RespostaDoAgente | Exception) -> TestClient:
        self.answerer = FakeAnswerer(ChatReply(text="Resposta do RAG."))
        app.dependency_overrides[get_chat_answerer] = lambda: self.answerer
        app.dependency_overrides[require_authenticated_user] = lambda: self.usuario
        app.dependency_overrides[get_conversa_repository] = lambda: self.espiao
        app.dependency_overrides[get_classificador_de_intencao] = lambda: (
            lambda texto: _detectada("gerar_alertas_pendencias", 0.9)
        )
        app.dependency_overrides[get_agente] = lambda: FakeAgente(resposta_do_agente)
        app.dependency_overrides[get_alerta_dispatcher] = lambda: _DispatcherEspiao()
        return TestClient(app, raise_server_exceptions=False)

    def test_recusa_nao_consulta_o_modelo(self) -> None:
        cliente = self._cliente(
            RespostaDoAgente(ResultadoAcao.RECUSADA_FORA_DO_CATALOGO, EntidadesExtraidas())
        )

        cliente.post(
            "/api/v1/chat",
            json={"message": "qual a previsão do tempo?", "conversation_id": _UUID_VALIDO},
        )

        self.assertEqual(self.answerer.chamadas, 0)

    def test_acao_de_portfolio_nao_consulta_o_modelo(self) -> None:
        pendencia = Pendencia(
            id=1, projeto_codigo="SYN-01", projeto_nome="Projeto", codigo=None,
            tipo="risco", titulo="Licença ambiental vencendo", descricao=None,
            criticidade=None, responsavel=None, prazo=None, situacao="aberta",
        )
        cliente = self._cliente(
            RespostaDoAgente(ResultadoAcao.PENDENCIAS, EntidadesExtraidas(), pendencias=(pendencia,))
        )

        corpo = cliente.post(
            "/api/v1/chat",
            json={"message": "o que precisa da minha atenção?", "conversation_id": _UUID_VALIDO},
        ).json()

        self.assertEqual(self.answerer.chamadas, 0)
        self.assertIn("Licença ambiental vencendo", corpo["reply"])

    def test_sem_acao_consulta_o_modelo_uma_vez(self) -> None:
        """O outro lado da asserção: sem ação, a conversa é a de sempre."""
        cliente = self._cliente(RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas()))

        corpo = cliente.post(
            "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
        ).json()

        self.assertEqual(self.answerer.chamadas, 1)
        self.assertEqual(corpo["reply"], "Resposta do RAG.")

    def test_agente_quebrado_cai_no_modelo(self) -> None:
        """Degradar é cair na conversa de sempre, e não devolver vazio.

        Com a classificação antes da geração, `executar_acao_sem_interferir`
        devolvendo None passou a ser o que DECIDE se o modelo é chamado. Um
        Agente com defeito não pode custar a resposta.
        """
        cliente = self._cliente(RuntimeError("agente quebrado"))

        with self.assertLogs("routes.chat", level="ERROR"):
            resposta = cliente.post(
                "/api/v1/chat", json={"message": "x", "conversation_id": _UUID_VALIDO}
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.answerer.chamadas, 1)
        self.assertEqual(resposta.json()["reply"], "Resposta do RAG.")


class TesteValidacaoAntesDaClassificacao(unittest.TestCase):
    """O 422 continua imediato, e não passa pelo classificador.

    A validação morava dentro de `AnswerChatMessage.answer`. Com a
    classificação subindo na ordem, deixá-la lá faria uma mensagem vazia chegar
    ao modelo de PLN, e o 422 passaria a depender do que ele achasse de uma
    string em branco.
    """

    def setUp(self) -> None:
        self.classificacoes: list[str] = []
        self.addCleanup(app.dependency_overrides.clear)

        def _classificador(texto: str):
            self.classificacoes.append(texto)
            return _detectada("gerar_alertas_pendencias", 0.9)

        self.answerer = FakeAnswerer(ChatReply(text="Resposta."))
        app.dependency_overrides[get_chat_answerer] = lambda: self.answerer
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        app.dependency_overrides[get_classificador_de_intencao] = lambda: _classificador
        # O Agente real consultaria o portfólio e pagaria o timeout do pool.
        # Aqui o que se mede é a ORDEM das etapas, não o que o Agente faz.
        app.dependency_overrides[get_agente] = lambda: FakeAgente(
            RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas())
        )
        self.cliente = TestClient(app, raise_server_exceptions=False)

    def test_mensagem_vazia_nao_chega_ao_classificador(self) -> None:
        resposta = self.cliente.post(
            "/api/v1/chat", json={"message": "   ", "conversation_id": _UUID_VALIDO}
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["error"], "empty_message")
        self.assertEqual(self.classificacoes, [])
        self.assertEqual(self.answerer.chamadas, 0)

    def test_mensagem_longa_demais_nao_chega_ao_classificador(self) -> None:
        resposta = self.cliente.post(
            "/api/v1/chat",
            json={"message": "x" * (MAX_MESSAGE_LENGTH + 1), "conversation_id": _UUID_VALIDO},
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["error"], "message_too_long")
        self.assertEqual(self.classificacoes, [])

    def test_classificador_ve_a_mensagem_sem_espacos_nas_pontas(self) -> None:
        """O mesmo texto para os dois.

        O handler classificava `payload.message` cru enquanto o modelo recebia
        a versão sem espaços. A intenção gravada na trilha não era, a rigor, a
        intenção do texto respondido.
        """
        self.cliente.post(
            "/api/v1/chat", json={"message": "  o que está pendente?  ", "conversation_id": _UUID_VALIDO}
        )

        self.assertEqual(self.classificacoes, ["o que está pendente?"])


class TesteClassificacaoChegaABusca(unittest.TestCase):
    """A ponta que faltava: a intenção influenciando o que a LLM enxerga.

    Antes desta integração a classificação era calculada, usada para decidir se
    o Agente agia, e descartada. Quando ele não agia, a pergunta ia ao RAG como
    se nenhuma classificação existisse.
    """

    def setUp(self) -> None:
        self.recebido: dict = {}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _cliente(self, intencao: str, confianca: float) -> TestClient:
        espiao = self

        class AnswererEspiao:
            def answer(self, message, conversation_id=None, foco=None):
                espiao.recebido["foco"] = foco
                return ChatReply(text="Resposta.", modelo="gemini-3.5-flash-lite")

        app.dependency_overrides[get_chat_answerer] = AnswererEspiao
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        app.dependency_overrides[get_classificador_de_intencao] = lambda: (
            lambda texto: _detectada(intencao, confianca)
        )
        return TestClient(app, raise_server_exceptions=False)

    def test_intencao_confiante_estreita_a_busca_por_tipo_de_documento(self) -> None:
        cliente = self._cliente("orientar_riscos_problemas", 0.95)

        cliente.post("/api/v1/chat", json={"message": "Como descrevo um risco?", "conversation_id": "c1"})

        self.assertEqual(self.recebido["foco"].tipo_documento, "riscos_problemas")

    def test_intencao_rejeitada_nao_estreita_nada(self) -> None:
        """O classificador inseguro não pode piorar o que funcionava sem ele."""
        cliente = self._cliente("orientar_riscos_problemas", 0.01)

        cliente.post("/api/v1/chat", json={"message": "Como descrevo um risco?", "conversation_id": "c1"})

        self.assertIsNone(self.recebido["foco"].tipo_documento)

    def test_codigo_do_projeto_chega_a_busca(self) -> None:
        # Extração por regra: não depende do F1 do classificador.
        cliente = self._cliente("consultar_documentos_normativos", 0.95)

        cliente.post("/api/v1/chat", json={"message": "Qual o risco do SYN-04?", "conversation_id": "c1"})

        self.assertEqual(self.recebido["foco"].projeto_codigo, "SYN-04")

    def test_sem_classificador_a_busca_continua_ampla(self) -> None:
        """Instalação sem o `.joblib` treinado segue conversando."""
        app.dependency_overrides[get_classificador_de_intencao] = lambda: None
        cliente = self._cliente("orientar_tap", 0.99)
        app.dependency_overrides[get_classificador_de_intencao] = lambda: None

        cliente.post("/api/v1/chat", json={"message": "Como preencho o TAP?", "conversation_id": "c1"})

        self.assertTrue(self.recebido["foco"].vazio)


if __name__ == "__main__":
    unittest.main()
