"""Contrato do webhook exercitado através da rota HTTP real, com o adaptador do
Microsoft Graph (TI-35 a TI-42).

Esta é a segunda subclasse de `ContratoWebhookInbound`. A primeira roda contra o
receptor em memória e verifica o serviço; esta atravessa o roteador do FastAPI e
verifica que a rota traduz corretamente cada causa em código de status —
inclusive o 5xx do caso TI-38, que é o que faz o provedor reentregar.

O adaptador do Graph é exercitado de verdade na tradução e nos dois
verificadores; o que continua substituído é apenas a persistência, que depende do
banco provisionado na Sprint 4.
"""

from __future__ import annotations

import json
import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from az1_api.dependencies import get_webhook_receiver_provider
from az1_api.main import app
from services.graph_push_service import (
    TradutorGraph,
    VerificadorAssinaturaAtiva,
    VerificadorClientState,
    VerificadorEmCadeia,
)
from services.webhook_service import ReceberEventoWebhook
from tests.test_integracao_contrato_webhook import (
    TIPO_CONHECIDO,
    AmbienteWebhook,
    ContratoWebhookInbound,
    Entrega,
    ProcessadorEmMemoria,
    RegistroEmMemoria,
)

CLIENT_STATE = "segredo-da-assinatura"
ROTA = "/api/v1/webhooks/microsoft"
ASSINATURA = "sub-1"

# O tradutor do Graph gera tipos no formato "graph.<changeType>". O catálogo do
# processador precisa falar a mesma língua, senão todo evento cairia no TI-40.
TIPO_GRAPH_CONHECIDO = "graph.updated"
TIPO_GRAPH_DESCONHECIDO = "graph.rebocado_por_um_trator"


def _daqui(dias: int) -> str:
    return (datetime.now(UTC) + timedelta(days=dias)).isoformat()


class ProcessadorGraph(ProcessadorEmMemoria):
    def suporta(self, tipo: str) -> bool:
        return tipo == TIPO_GRAPH_CONHECIDO


class ConexoesEmMemoria:
    """Dublê de `integracao.conexao` para a verificação de assinatura viva."""

    def __init__(self, ativas: set[str]) -> None:
        self.ativas = ativas

    def assinatura_ativa(self, subscription_id: str) -> bool:
        return subscription_id in self.ativas


class AmbienteHTTP(AmbienteWebhook):
    def __init__(self) -> None:
        self.registro = RegistroEmMemoria()
        self.processador = ProcessadorGraph()
        self.conexoes = ConexoesEmMemoria(ativas={ASSINATURA})
        receptor = ReceberEventoWebhook(
            verificador=VerificadorEmCadeia(
                verificadores=(
                    VerificadorClientState(esperado=CLIENT_STATE),
                    VerificadorAssinaturaAtiva(conexoes=self.conexoes),
                )
            ),
            tradutor=TradutorGraph(),
            registro=self.registro,
            processador=self.processador,
        )
        app.dependency_overrides[get_webhook_receiver_provider] = lambda: lambda: receptor
        self.cliente = TestClient(app, raise_server_exceptions=False)

    def entregar(self, entrega: Entrega) -> int:
        resposta = self.cliente.post(ROTA, content=entrega.corpo, headers=dict(entrega.cabecalhos))
        return resposta.status_code

    def _notificacao(
        self,
        *,
        change_type: str,
        item_id: str,
        client_state: str | None = CLIENT_STATE,
        assinatura: str = ASSINATURA,
        expira_em: str | None = None,
    ) -> dict[str, object]:
        notificacao: dict[str, object] = {
            "subscriptionId": assinatura,
            "changeType": change_type,
            "resource": "drives/b!fake/root",
            "id": item_id,
            "resourceData": {"id": item_id, "@odata.type": "#microsoft.graph.driveItem"},
            "tenantId": "tenant-1",
            "subscriptionExpirationDateTime": expira_em or _daqui(29),
        }
        if client_state is not None:
            notificacao["clientState"] = client_state
        return notificacao

    def _entrega(self, *notificacoes: dict[str, object]) -> Entrega:
        return Entrega(
            cabecalhos={"content-type": "application/json"},
            corpo=json.dumps({"value": list(notificacoes)}).encode(),
        )

    def entrega_valida(self, *, tipo: str = TIPO_CONHECIDO, identificador: str = "evt-1") -> Entrega:
        change_type = "updated" if tipo == TIPO_CONHECIDO else tipo.removeprefix("graph.")
        return self._entrega(self._notificacao(change_type=change_type, item_id=identificador))

    def entregas_de_lote(self, *, quantidade: int) -> Sequence[Entrega]:
        # O Graph agrupa mudanças próximas: uma entrega só, com várias dentro.
        return [
            self._entrega(
                *(self._notificacao(change_type="updated", item_id=f"item-{indice}") for indice in range(quantidade))
            )
        ]

    def entrega_sem_assinatura(self) -> Entrega:
        return self._entrega(self._notificacao(change_type="updated", item_id="evt-sem", client_state=None))

    def entrega_com_assinatura_incorreta(self) -> Entrega:
        return self._entrega(
            self._notificacao(change_type="updated", item_id="evt-errado", client_state="segredo-errado")
        )

    def entrega_com_assinatura_antiga(self) -> Entrega:
        # A terceira causa do TI-36. O `clientState` confere — quem capturou uma
        # entrega antiga tem o segredo, porque ele viaja no próprio corpo. O que
        # recusa a entrega é a validade da assinatura ter passado.
        return self._entrega(self._notificacao(change_type="updated", item_id="evt-antigo", expira_em=_daqui(-1)))

    def entrega_malformada(self) -> Entrega:
        # Autenticada e ainda assim inválida: sem `subscriptionId` não há como
        # montar o identificador do evento. Deixar de fora o `clientState` aqui
        # testaria a causa errada — seria recusada como 401 antes de a estrutura
        # ser sequer olhada.
        return Entrega(
            cabecalhos={"content-type": "application/json"},
            corpo=json.dumps(
                {"value": [{"changeType": "updated", "resource": "r", "clientState": CLIENT_STATE}]}
            ).encode(),
        )

    def efeitos_aplicados(self) -> int:
        return self.processador.efeitos

    def eventos_registrados(self) -> int:
        return len(self.registro.eventos) + len(self.registro.recusas)

    def quebrar_processamento(self, *, depois_de: int = 0) -> None:
        self.processador.quebrar_em = depois_de


class TestContratoWebhookHTTP(ContratoWebhookInbound, unittest.TestCase):
    """Exercita o contrato contra a rota real do FastAPI."""

    def construir_ambiente(self) -> AmbienteWebhook:
        return AmbienteHTTP()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_evento_de_tipo_desconhecido_e_registrado_e_ignorado(self) -> None:
        entrega = self.ambiente.entrega_valida(tipo=TIPO_GRAPH_DESCONHECIDO, identificador="evt-exotico")

        resposta = self.ambiente.entregar(entrega)

        self.assertIn(resposta, range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 1)


class TestVerificadorAssinaturaAtiva(unittest.TestCase):
    """A parte da autenticidade que o `clientState` sozinho não cobre.

    O `clientState` é constante durante toda a vida da assinatura e viaja no
    corpo da notificação, então quem capturou uma entrega tem o segredo para
    sempre. Estes dois casos são o que impede essa captura de valer indefinidamente.
    """

    def setUp(self) -> None:
        self.ambiente = AmbienteHTTP()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_assinatura_desconhecida_e_recusada(self) -> None:
        entrega = self.ambiente._entrega(
            self.ambiente._notificacao(change_type="updated", item_id="i1", assinatura="sub-fantasma")
        )

        self.assertEqual(self.ambiente.entregar(entrega), 401)
        self.assertEqual(self.ambiente.eventos_registrados(), 0)

    def test_assinatura_desativada_deixa_de_ser_aceita(self) -> None:
        entrega = self.ambiente.entrega_valida(identificador="i1")
        self.assertIn(self.ambiente.entregar(entrega), range(200, 300))

        # Apagar a assinatura no Graph, ou desativá-la em integracao.conexao,
        # invalida imediatamente qualquer entrega capturada antes.
        self.ambiente.conexoes.ativas.clear()

        self.assertEqual(self.ambiente.entregar(self.ambiente.entrega_valida(identificador="i2")), 401)


class TestHandshakeDeValidacao(unittest.TestCase):
    """O handshake que o Graph faz ao criar a assinatura.

    Se esta resposta não for exatamente 200, text/plain e o token em texto puro,
    a assinatura não chega a ser criada e nenhuma notificação jamais é entregue.
    """

    def setUp(self) -> None:
        self.cliente = TestClient(app)

    def test_devolve_o_token_em_texto_puro(self) -> None:
        resposta = self.cliente.post(ROTA, params={"validationToken": "abc 123+/="})

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.headers["content-type"].startswith("text/plain"))
        self.assertEqual(resposta.text, "abc 123+/=")

    def test_handshake_nao_depende_do_receptor(self) -> None:
        # Nenhum override registrado: o handshake precisa responder mesmo antes
        # de o receptor estar montado, senão a assinatura não pode ser criada
        # numa instalação nova.
        app.dependency_overrides.clear()

        resposta = self.cliente.post(ROTA, params={"validationToken": "tok"})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.text, "tok")


class TestTradutorGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.tradutor = TradutorGraph()

    def test_identificador_combina_assinatura_e_item(self) -> None:
        corpo = json.dumps(
            {
                "value": [
                    {"subscriptionId": "s1", "changeType": "updated", "resource": "r", "resourceData": {"id": "i1", "@odata.etag": "v1"}}
                ]
            }
        ).encode()

        eventos = self.tradutor.traduzir(cabecalhos={}, corpo=corpo)

        # O identificador precisa distinguir o mesmo item vindo de assinaturas
        # diferentes, senão trocar de conexão faria o evento novo parecer duplicata.
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].identificador, "s1:i1:v1")
        self.assertEqual(eventos[0].tipo, "graph.updated")
        self.assertEqual(eventos[0].correlacao, "s1")

    def test_entrega_com_varias_mudancas_e_desdobrada(self) -> None:
        notificacao = {"subscriptionId": "s1", "changeType": "updated", "resource": "r"}
        corpo = json.dumps(
            {"value": [{**notificacao, "resourceData": {"id": "i1", "@odata.etag": "v1"}}, {**notificacao, "resourceData": {"id": "i2", "@odata.etag": "v1"}}]}
        ).encode()

        eventos = self.tradutor.traduzir(cabecalhos={}, corpo=corpo)

        self.assertEqual([e.identificador for e in eventos], ["s1:i1:v1", "s1:i2:v1"])


class TestAvisosOneDrive(unittest.TestCase):
    def setUp(self):
        self.ambiente = AmbienteHTTP()
        self.addCleanup(app.dependency_overrides.clear)

    def aviso(self, **campos):
        return {"subscriptionId": ASSINATURA, "expirationDateTime": _daqui(1),
                "resource": "/me/drive/root", "clientState": CLIENT_STATE, **campos}

    def enviar(self, aviso):
        return self.ambiente.cliente.post("/api/v1/webhooks/microsoft", json={"value": [aviso]})

    def test_payload_minimo_oficial_aceito_e_nova_mudanca_nao_e_descartada(self):
        for _ in range(2):
            self.assertEqual(self.enviar(self.aviso()).status_code, 202)
        self.assertEqual(self.ambiente.eventos_registrados(), 2)
        self.assertEqual(self.ambiente.efeitos_aplicados(), 2)

    def test_expiracao_do_onedrive_e_respeitada(self):
        self.assertEqual(self.enviar(self.aviso(expirationDateTime=_daqui(-1))).status_code, 401)
        self.assertEqual(self.ambiente.eventos_registrados(), 0)

    def test_tipos_invalidos_nao_produzem_erro_interno(self):
        for campo, valor in [("resource", []), ("resourceData", []), ("id", []),
                             ("changeType", None), ("subscriptionId", []),
                             ("expirationDateTime", "2026-09-11")]:
            with self.subTest(campo=campo):
                self.assertEqual(self.enviar(self.aviso(**{campo: valor})).status_code, 400)
        for valor in [1, {}, "segredo-incorreto", "ç"]:
            with self.subTest(clientState=valor):
                self.assertEqual(self.enviar(self.aviso(clientState=valor)).status_code, 401)
        self.assertEqual(self.enviar(None).status_code, 400)
        self.assertEqual(self.ambiente.cliente.post(ROTA, content=b"\xff").status_code, 400)

    def test_item_sem_versao_nao_e_chave_de_deduplicacao(self):
        corpo = json.dumps({"value": [self.aviso(resourceData={"id": "mesmo-item"})]}).encode()
        a = TradutorGraph().traduzir(cabecalhos={}, corpo=corpo)[0]
        b = TradutorGraph().traduzir(cabecalhos={}, corpo=corpo)[0]
        self.assertNotEqual(a.identificador, b.identificador)

    def test_versoes_diferentes_do_item_produzem_chaves_diferentes(self):
        def traduzir(etag):
            corpo = json.dumps({"value": [self.aviso(resourceData={"id": "item", "@odata.etag": etag})]}).encode()
            return TradutorGraph().traduzir(cabecalhos={}, corpo=corpo)[0].identificador
        self.assertEqual(traduzir("v1"), traduzir("v1"))
        self.assertNotEqual(traduzir("v1"), traduzir("v2"))
