"""Contrato do webhook exercitado com o adaptador do Google Drive (TI-35 a TI-42).

Terceira subclasse de `ContratoWebhookInbound`, e a que dá sentido ao esforço de
ter escrito o contrato sem citar provedor: os oito casos abaixo não foram
escritos para o Drive nem adaptados a ele. São os mesmos herdados, e o que muda é
só como uma entrega é forjada.

O Drive difere do Graph em duas coisas que o contrato absorve sem alteração:

* o corpo chega **vazio** e a informação vem toda em cabeçalhos `X-Goog-*`,
  enquanto o Graph faz o contrário;
* o Drive não agrupa mudanças, então três mudanças chegam em três entregas
  separadas, enquanto o Graph manda uma entrega com três dentro.
"""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from az1_api.dependencies import get_drive_webhook_receiver_provider
from az1_api.main import app
from services.drive_push_service import (
    TradutorDrive,
    VerificadorCanalAtivo,
    VerificadorChannelToken,
)
from services.graph_push_service import VerificadorEmCadeia
from services.webhook_service import ReceberEventoWebhook
from tests.test_integracao_contrato_webhook import (
    TIPO_CONHECIDO,
    AmbienteWebhook,
    ContratoWebhookInbound,
    Entrega,
    ProcessadorEmMemoria,
    RegistroEmMemoria,
)
from tests.test_integracao_webhook import ConexoesEmMemoria

CHANNEL_TOKEN = "segredo-do-canal"
ROTA = "/api/v1/webhooks/google"
CANAL = "canal-1"

TIPO_DRIVE_CONHECIDO = "drive.change"
TIPO_DRIVE_DESCONHECIDO = "drive.rebocado_por_um_trator"


def _data_http(dias: int) -> str:
    """Formata como o Google formata: data HTTP (RFC 2822), não ISO 8601."""
    instante = datetime.now(UTC) + timedelta(days=dias)
    return instante.strftime("%a, %d %b %Y %H:%M:%S GMT")


class ProcessadorDrive(ProcessadorEmMemoria):
    def suporta(self, tipo: str) -> bool:
        return tipo == TIPO_DRIVE_CONHECIDO


class AmbienteDriveHTTP(AmbienteWebhook):
    def __init__(self) -> None:
        self.registro = RegistroEmMemoria()
        self.processador = ProcessadorDrive()
        self.conexoes = ConexoesEmMemoria(ativas={CANAL})
        receptor = ReceberEventoWebhook(
            verificador=VerificadorEmCadeia(
                verificadores=(
                    VerificadorChannelToken(esperado=CHANNEL_TOKEN),
                    VerificadorCanalAtivo(conexoes=self.conexoes),
                )
            ),
            tradutor=TradutorDrive(),
            registro=self.registro,
            processador=self.processador,
        )
        app.dependency_overrides[get_drive_webhook_receiver_provider] = lambda: lambda: receptor
        self.cliente = TestClient(app, raise_server_exceptions=False)

    def entregar(self, entrega: Entrega) -> int:
        # `content` vazio de propósito: é assim que o Drive entrega, e é o que
        # obriga o tradutor a ler os cabeçalhos.
        resposta = self.cliente.post(ROTA, content=entrega.corpo, headers=dict(entrega.cabecalhos))
        return resposta.status_code

    def _cabecalhos(
        self,
        *,
        estado: str,
        numero: str,
        canal: str = CANAL,
        token: str | None = CHANNEL_TOKEN,
        expira_em: str | None = None,
    ) -> dict[str, str]:
        cabecalhos = {
            "x-goog-channel-id": canal,
            "x-goog-message-number": numero,
            "x-goog-resource-state": estado,
            "x-goog-resource-id": "recurso-abc",
            "x-goog-resource-uri": "https://www.googleapis.com/drive/v3/changes?alt=json",
            "x-goog-channel-expiration": expira_em or _data_http(7),
        }
        if token is not None:
            cabecalhos["x-goog-channel-token"] = token
        return cabecalhos

    def _entrega(self, **kwargs: str | None) -> Entrega:
        return Entrega(cabecalhos=self._cabecalhos(**kwargs), corpo=b"")  # type: ignore[arg-type]

    def entrega_valida(self, *, tipo: str = TIPO_CONHECIDO, identificador: str = "evt-1") -> Entrega:
        estado = "change" if tipo == TIPO_CONHECIDO else tipo.removeprefix("drive.")
        # O número da mensagem é tratado como opaco pelo receptor — nunca é lido
        # como inteiro —, por isso o teste pode usar um valor legível no lugar da
        # sequência numérica que o Drive emite de verdade.
        return self._entrega(estado=estado, numero=identificador)

    def entregas_de_lote(self, *, quantidade: int) -> Sequence[Entrega]:
        # O Drive não agrupa: cada mudança vira uma notificação própria.
        return [self._entrega(estado="change", numero=f"{indice + 2}") for indice in range(quantidade)]

    def entrega_sem_assinatura(self) -> Entrega:
        return self._entrega(estado="change", numero="sem-token", token=None)

    def entrega_com_assinatura_incorreta(self) -> Entrega:
        return self._entrega(estado="change", numero="token-errado", token="segredo-errado")

    def entrega_com_assinatura_antiga(self) -> Entrega:
        # O token confere — quem capturou a entrega tem o segredo, porque ele
        # viaja no cabeçalho. O que recusa é a validade do canal ter passado.
        return self._entrega(estado="change", numero="antigo", expira_em=_data_http(-1))

    def entrega_malformada(self) -> Entrega:
        # Autenticada e ainda assim inválida: sem número de mensagem não há chave
        # de idempotência, então o evento não pode ser aceito.
        cabecalhos = self._cabecalhos(estado="change", numero="1")
        del cabecalhos["x-goog-message-number"]
        return Entrega(cabecalhos=cabecalhos, corpo=b"")

    def efeitos_aplicados(self) -> int:
        return self.processador.efeitos

    def eventos_registrados(self) -> int:
        return len(self.registro.eventos) + len(self.registro.recusas)

    def quebrar_processamento(self, *, depois_de: int = 0) -> None:
        self.processador.quebrar_em = depois_de


class TestContratoWebhookDrive(ContratoWebhookInbound, unittest.TestCase):
    """Exercita o contrato contra a rota do Drive."""

    def construir_ambiente(self) -> AmbienteWebhook:
        return AmbienteDriveHTTP()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_evento_de_tipo_desconhecido_e_registrado_e_ignorado(self) -> None:
        entrega = self.ambiente.entrega_valida(tipo=TIPO_DRIVE_DESCONHECIDO, identificador="evt-exotico")

        self.assertIn(self.ambiente.entregar(entrega), range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 1)


class TestMensagemDeAberturaDoCanal(unittest.TestCase):
    """O `sync`, que é o equivalente funcional do handshake do Graph.

    O Drive não valida a URL antes de abrir o canal: ele abre e manda como
    primeira entrega uma notificação de estado `sync`, número 1. Ela não
    representa mudança nenhuma no acervo, então precisa ser confirmada e
    descartada — que é exatamente o comportamento do caso TI-40.
    """

    def setUp(self) -> None:
        self.ambiente = AmbienteDriveHTTP()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_sync_e_confirmado_e_nao_produz_efeito(self) -> None:
        entrega = self.ambiente._entrega(estado="sync", numero="1")

        self.assertIn(self.ambiente.entregar(entrega), range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 1)


class TestTradutorDrive(unittest.TestCase):
    def setUp(self) -> None:
        self.tradutor = TradutorDrive()

    def test_le_os_cabecalhos_e_ignora_o_corpo_vazio(self) -> None:
        eventos = self.tradutor.traduzir(
            cabecalhos={
                "X-Goog-Channel-ID": "c1",
                "X-Goog-Message-Number": "42",
                "X-Goog-Resource-State": "change",
                "X-Goog-Resource-ID": "r1",
            },
            corpo=b"",
        )

        # Chaves em maiúsculas de propósito: cabeçalho HTTP não diferencia caixa,
        # e o tradutor normaliza antes de ler.
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].identificador, "c1:42")
        self.assertEqual(eventos[0].tipo, "drive.change")
        self.assertEqual(eventos[0].correlacao, "c1")
        self.assertEqual(eventos[0].conteudo["resource_id"], "r1")
