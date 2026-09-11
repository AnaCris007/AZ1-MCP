"""Contrato exercitado contra o Postgres de verdade (TI-35 a TI-42).

Quarta subclasse de `ContratoWebhookInbound`, e a que fecha a exigência da Seção
6.4 de que "a persistência ocorre em serviços reais e não em dublês de memória".
As três anteriores trocam o registro por um dicionário; esta usa
`auditoria.evento_webhook`.

O que está sob teste aqui é a idempotência do caso TI-37, e ela não está escrita
em Python: é a restrição `UNIQUE (provedor, subscription_id, notificacao_id)` do
esquema. Um teste com dublê em memória confirmaria apenas que o dicionário do
dublê funciona — o que precisa ser provado é que a restrição existe, cobre as
colunas certas e é observada corretamente pelo `ON CONFLICT`.

O processador continua sendo o dublê em memória de propósito: o efeito real
(`delta_pendente`) é um booleano, e um booleano não permite distinguir "aplicado
uma vez" de "aplicado três vezes", que é justamente o que os casos precisam
contar. O processador de verdade é verificado à parte, no final do arquivo.

Requer o serviço `postgres` do docker-compose no ar:

    docker compose up -d postgres

Sem ele, a suíte inteira é pulada em vez de falhar.
"""

from __future__ import annotations

import os
import threading
import time
import unittest

import psycopg
from psycopg_pool import ConnectionPool

from az1_api.dependencies import get_drive_webhook_receiver_provider
from az1_api.main import app
from services.drive_push_service import PROVEDOR as PROVEDOR_DRIVE
from services.drive_push_service import TIPOS_PROCESSAVEIS as TIPOS_DRIVE
from services.drive_push_service import (
    TradutorDrive,
    VerificadorCanalAtivo,
    VerificadorChannelToken,
)
from services.graph_push_service import VerificadorEmCadeia
from services.webhook_registry_service import (
    ProcessadorVarreduraPendente,
    RegistroConexoesPostgres,
    RegistroEventosPostgres,
)
from services.webhook_service import EventoWebhook, ReceberEventoWebhook, SituacaoEvento
from tests.test_integracao_contrato_webhook import (
    AmbienteWebhook,
    ContratoWebhookInbound,
    ProcessadorEmMemoria,
)
from tests.test_integracao_webhook_drive import CANAL, CHANNEL_TOKEN, AmbienteDriveHTTP

DSN = os.environ.get("TEST_DATABASE_URL")


def _banco_disponivel() -> str | None:
    """Devolve o motivo de pular, ou None se o banco de teste responder.

    Não cai para DATABASE_URL, e recusa mesmo que os dois apontem para o
    mesmo lugar. Esta suíte é destrutiva -- TRUNCATE em auditoria.evento_webhook
    e DELETE em integracao.conexao a cada teste --, e um fallback silencioso
    apagaria dados reais de demonstração sem aviso algum. Foi exatamente isso
    que aconteceu uma vez neste projeto: rodar a suíte inteira sem
    TEST_DATABASE_URL definido apagou o canal do Google Drive que sustentava a
    evidência da Seção 5.1.6. Só roda contra um banco declarado
    explicitamente para teste, e diferente do banco da aplicação.
    """
    if not DSN:
        return "TEST_DATABASE_URL não definido. Aponte para um banco de teste dedicado -- nunca para DATABASE_URL."
    if os.environ.get("DATABASE_URL") == DSN:
        return "TEST_DATABASE_URL é igual a DATABASE_URL. Esta suíte é destrutiva; use um banco de teste separado."
    try:
        with psycopg.connect(DSN, connect_timeout=3) as conexao:
            conexao.execute("SELECT 1 FROM auditoria.evento_webhook LIMIT 0")
    except psycopg.OperationalError as exc:
        return f"Postgres indisponível em {DSN}: {exc}".strip()
    except psycopg.Error as exc:
        return f"Esquema ausente — rode o DDL de src/database: {exc}".strip()
    return None


MOTIVO = _banco_disponivel()


def _limpar(pool: ConnectionPool) -> None:
    with pool.connection() as conexao:
        conexao.execute("TRUNCATE auditoria.evento_webhook RESTART IDENTITY CASCADE")
        conexao.execute("DELETE FROM integracao.conexao WHERE provedor = %s", (PROVEDOR_DRIVE,))
        conexao.execute(
            """
            INSERT INTO integracao.conexao
                (provedor, conta, recurso, client_state, subscription_id, ativa)
            VALUES (%s, 'teste', 'changes', %s, %s, TRUE)
            """,
            (PROVEDOR_DRIVE, CHANNEL_TOKEN, CANAL),
        )


class AmbientePostgres(AmbienteDriveHTTP):
    """Mesmo ambiente do Drive, com a persistência trocada pela de verdade."""

    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool
        _limpar(pool)

        self.registro = RegistroEventosPostgres(pool, PROVEDOR_DRIVE)
        self.processador = ProcessadorEmMemoria()
        self.processador.suporta = lambda tipo: tipo == "drive.change"  # type: ignore[method-assign]

        receptor = ReceberEventoWebhook(
            verificador=VerificadorEmCadeia(
                verificadores=(
                    VerificadorChannelToken(esperado=CHANNEL_TOKEN),
                    VerificadorCanalAtivo(conexoes=RegistroConexoesPostgres(pool, PROVEDOR_DRIVE)),
                )
            ),
            tradutor=TradutorDrive(),
            registro=self.registro,
            processador=self.processador,
        )
        app.dependency_overrides[get_drive_webhook_receiver_provider] = lambda: lambda: receptor

        from fastapi.testclient import TestClient

        self.cliente = TestClient(app, raise_server_exceptions=False)

    def eventos_registrados(self) -> int:
        with self.pool.connection() as conexao:
            linha = conexao.execute("SELECT count(*) FROM auditoria.evento_webhook").fetchone()
        return int(linha[0]) if linha else 0


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class TestContratoWebhookPostgres(ContratoWebhookInbound, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pool = ConnectionPool(DSN, min_size=1, max_size=3, open=False)
        cls.pool.open()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()

    def construir_ambiente(self) -> AmbienteWebhook:
        return AmbientePostgres(self.pool)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_evento_de_tipo_desconhecido_e_registrado_e_ignorado(self) -> None:
        entrega = self.ambiente.entrega_valida(tipo="drive.exotico", identificador="evt-exotico")

        self.assertIn(self.ambiente.entregar(entrega), range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 1)


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class TestPersistenciaDoEvento(unittest.TestCase):
    """O que fica gravado, além de quantos eventos existem."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pool = ConnectionPool(DSN, min_size=1, max_size=3, open=False)
        cls.pool.open()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()

    def setUp(self) -> None:
        _limpar(self.pool)
        self.registro = RegistroEventosPostgres(self.pool, PROVEDOR_DRIVE)

    def _evento(self, identificador: str = f"{CANAL}:7") -> EventoWebhook:
        from datetime import UTC, datetime

        return EventoWebhook(
            identificador=identificador,
            tipo="drive.change",
            versao="1",
            marca_de_tempo=datetime.now(UTC),
            correlacao=CANAL,
            conteudo={"provedor": PROVEDOR_DRIVE, "channel_id": CANAL, "message_number": "7"},
        )

    def test_reivindicacao_e_duplicata_apos_concluida(self) -> None:
        """TI-37, sem concorrência: uma vez concluída, mais ninguém reivindica."""
        evento = self._evento()

        reivindicacao = self.registro.reivindicar(evento)
        self.assertIsNotNone(reivindicacao)
        reivindicacao.concluir(SituacaoEvento.PROCESSADO)

        self.assertIsNone(self.registro.reivindicar(evento))

        with self.pool.connection() as conexao:
            linha = conexao.execute(
                "SELECT count(*), min(situacao) FROM auditoria.evento_webhook WHERE notificacao_id = '7'"
            ).fetchone()

        # Uma linha só: a segunda chamada não inseriu nem reivindicou de novo.
        self.assertEqual(linha, (1, "processado"))

    def test_reivindicacao_concorrente_espera_e_ve_a_conclusao(self) -> None:
        """Prova com duas threads de verdade que a segunda espera a primeira —
        e não decide por uma leitura tirada antes de a primeira terminar.

        É o cenário observado na demonstração ao vivo: o Google reentregou a
        mesma mudança por dois caminhos quase ao mesmo tempo. A ordem registrada
        abaixo só pode sair como está se `reivindicar` da thread B tiver
        bloqueado dentro do Postgres até a thread A concluir — não é apenas o
        valor final que está sob teste, é o bloqueio em si.
        """
        evento = self._evento()
        a_reivindicou = threading.Event()
        ordem: list[str] = []

        def tentativa_a() -> None:
            reivindicacao = self.registro.reivindicar(evento)
            assert reivindicacao is not None
            a_reivindicou.set()
            time.sleep(0.3)  # segura o lock por tempo perceptível
            ordem.append("a_concluiu")
            reivindicacao.concluir(SituacaoEvento.PROCESSADO)

        resultado_b: list[object] = []

        def tentativa_b() -> None:
            a_reivindicou.wait(timeout=5)
            resultado_b.append(self.registro.reivindicar(evento))
            ordem.append("b_desbloqueou")

        thread_a = threading.Thread(target=tentativa_a)
        thread_b = threading.Thread(target=tentativa_b)
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

        # B só desbloqueou depois que A concluiu, nunca antes.
        self.assertEqual(ordem, ["a_concluiu", "b_desbloqueou"])
        # E viu o estado definitivo: já concluído, portanto duplicata.
        self.assertIsNone(resultado_b[0])

    def test_reivindicacao_concorrente_retoma_apos_a_primeira_liberar(self) -> None:
        """A reentrega de verdade do TI-38 — a primeira tentativa falhou.

        Distinto do teste acima só no desfecho da thread A: aqui ela libera
        (simulando falha de processamento) em vez de concluir. A thread B,
        destravada em seguida, precisa conseguir reivindicar de verdade — é
        essa retomada que TI-38 exige, e ela precisa sobreviver ao mesmo lock
        que agora serializa o caso concorrente.
        """
        evento = self._evento()
        a_reivindicou = threading.Event()
        ordem: list[str] = []

        def tentativa_a() -> None:
            reivindicacao = self.registro.reivindicar(evento)
            assert reivindicacao is not None
            a_reivindicou.set()
            time.sleep(0.3)
            ordem.append("a_liberou")
            reivindicacao.liberar()

        resultado_b: list[object] = []

        def tentativa_b() -> None:
            a_reivindicou.wait(timeout=5)
            resultado_b.append(self.registro.reivindicar(evento))
            ordem.append("b_desbloqueou")

        thread_a = threading.Thread(target=tentativa_a)
        thread_b = threading.Thread(target=tentativa_b)
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

        self.assertEqual(ordem, ["a_liberou", "b_desbloqueou"])
        self.assertIsNotNone(resultado_b[0])
        resultado_b[0].concluir(SituacaoEvento.PROCESSADO)

        with self.pool.connection() as conexao:
            linha = conexao.execute(
                "SELECT count(*), min(situacao) FROM auditoria.evento_webhook WHERE notificacao_id = '7'"
            ).fetchone()

        # Uma linha só, apesar das duas reivindicações: a unicidade é do esquema.
        self.assertEqual(linha, (1, "processado"))

    def test_recusa_grava_o_corpo_bruto_sem_envelope(self) -> None:
        self.registro.registrar_recusa(motivo="CONTEUDO_MALFORMADO", corpo=b'{"torto": true}')

        with self.pool.connection() as conexao:
            linha = conexao.execute(
                "SELECT situacao, motivo, corpo_bruto, notificacao_id FROM auditoria.evento_webhook"
            ).fetchone()

        self.assertEqual(linha, ("recusado", "CONTEUDO_MALFORMADO", '{"torto": true}', None))

    def test_processador_marca_varredura_pendente(self) -> None:
        processador = ProcessadorVarreduraPendente(self.pool, PROVEDOR_DRIVE, TIPOS_DRIVE)

        self.assertTrue(processador.suporta("drive.change"))
        self.assertFalse(processador.suporta("drive.sync"))

        processador.processar(self._evento())

        with self.pool.connection() as conexao:
            linha = conexao.execute(
                "SELECT delta_pendente FROM integracao.conexao WHERE subscription_id = %s", (CANAL,)
            ).fetchone()

        self.assertEqual(linha, (True,))
