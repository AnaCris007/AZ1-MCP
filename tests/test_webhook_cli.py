"""Testes das ferramentas de linha de comando das duas origens.

Cobrem apenas o que não depende de rede: leitura de configuração, montagem de
URL e formato de erro. É deliberadamente pouco — o valor destes scripts está na
conversa com o provedor, que só um ambiente real exercita.

Existem porque o script do Graph não pôde ser executado ponta a ponta (ver Seção
5.1.1 do Projeto.md) e, sem eles, nem a validação de configuração teria sido
verificada uma vez.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from services.graph_subscription_service import Config as ConfigGraph
from services.webhook_http import ErroDeOperacao, ErroHTTP

AMBIENTE_GRAPH = {
    "MS_CLIENT_ID": "11111111-2222-3333-4444-555555555555",
    "MS_WEBHOOK_CLIENT_STATE": "segredo",
    "WEBHOOK_PUBLIC_URL": "https://exemplo.trycloudflare.com/",
}


class TestConfigGraph(unittest.TestCase):
    def test_monta_a_url_de_notificacao_sem_barra_dobrada(self) -> None:
        with mock.patch.dict(os.environ, AMBIENTE_GRAPH, clear=True):
            config = ConfigGraph.from_environment()

        # A barra final do .env é comum e produziria `//api/v1/...`, que o Graph
        # aceita registrar mas entrega em uma rota que não existe.
        self.assertEqual(config.notification_url, "https://exemplo.trycloudflare.com/api/v1/webhooks/microsoft")

    def test_recusa_url_sem_https(self) -> None:
        ambiente = {**AMBIENTE_GRAPH, "WEBHOOK_PUBLIC_URL": "http://localhost:8000"}

        with mock.patch.dict(os.environ, ambiente, clear=True), self.assertRaises(ErroDeOperacao) as capturado:
            ConfigGraph.from_environment()

        # O Graph exige HTTPS e devolve um erro genérico quando não é; falhar
        # antes da chamada economiza a depuração daquele erro.
        self.assertIn("https://", str(capturado.exception))

    def test_lista_todas_as_variaveis_ausentes_de_uma_vez(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(ErroDeOperacao) as capturado:
            ConfigGraph.from_environment()

        mensagem = str(capturado.exception)
        for variavel in ("MS_CLIENT_ID", "MS_WEBHOOK_CLIENT_STATE", "WEBHOOK_PUBLIC_URL"):
            self.assertIn(variavel, mensagem)

    def test_recurso_e_tenant_tem_padrao_de_desenvolvimento(self) -> None:
        with mock.patch.dict(os.environ, AMBIENTE_GRAPH, clear=True):
            config = ConfigGraph.from_environment()

        self.assertEqual(config.recurso, "/me/drive/root")
        self.assertEqual(config.tenant, "consumers")
        self.assertTrue(config.autoridade("devicecode").endswith("/consumers/oauth2/v2.0/devicecode"))

    def test_recurso_de_producao_e_so_uma_variavel(self) -> None:
        ambiente = {**AMBIENTE_GRAPH, "MS_RECURSO": "/drives/b!x9K/root", "MS_TENANT": "9f4ebab6-520d-49c0"}

        with mock.patch.dict(os.environ, ambiente, clear=True):
            config = ConfigGraph.from_environment()

        self.assertEqual(config.recurso, "/drives/b!x9K/root")
        self.assertIn("9f4ebab6-520d-49c0", config.autoridade("token"))


class TestErroHTTP(unittest.TestCase):
    def test_expoe_o_codigo_do_provedor(self) -> None:
        # O laço do fluxo de código de dispositivo decide continuar ou parar por
        # este campo, e não pelo status: `authorization_pending` também é 400.
        erro = ErroHTTP(400, {"error": "authorization_pending"}, "https://exemplo")

        self.assertEqual(erro.codigo, "authorization_pending")
        self.assertEqual(erro.status, 400)

    def test_corpo_nao_json_nao_quebra(self) -> None:
        erro = ErroHTTP(502, "<html>Bad Gateway</html>", "https://exemplo")

        self.assertEqual(erro.codigo, "")
        self.assertIn("Bad Gateway", str(erro))


class TestAberturaDrive(unittest.TestCase):
    def test_canal_ativo_nao_dispara_watch_nem_compensacao(self):
        from services import drive_channel_service as drive
        config = drive.Config("id", "secret", "token", "https://example.org", "dsn")
        with (mock.patch.object(drive, "obter_token", return_value="access"),
              mock.patch.object(drive, "_pedir", return_value={"startPageToken": "inicio"}) as pedir,
              mock.patch.object(drive.psycopg, "connect") as connect):
            conn = connect.return_value.__enter__.return_value
            conn.execute.return_value.fetchone.return_value = None
            with self.assertRaisesRegex(ErroDeOperacao, "Já existe um canal ativo"):
                drive.abrir(config)
            self.assertEqual(pedir.call_count, 1)
            self.assertEqual(conn.execute.call_count, 1)

    def test_falha_watch_desativa_apenas_a_reserva_nova(self):
        from services import drive_channel_service as drive
        config = drive.Config("id", "secret", "token", "https://example.org", "dsn")
        with (mock.patch.object(drive, "obter_token", return_value="access"),
              mock.patch.object(drive, "_pedir", side_effect=[{"startPageToken": "inicio"}, ErroDeOperacao("watch falhou")]),
              mock.patch.object(drive.uuid, "uuid4", return_value="novo-canal"),
              mock.patch.object(drive.psycopg, "connect") as connect):
            conn = connect.return_value.__enter__.return_value
            conn.execute.return_value.fetchone.return_value = (1,)
            with self.assertRaisesRegex(ErroDeOperacao, "watch falhou"):
                drive.abrir(config)
            self.assertEqual(conn.execute.call_count, 2)
            self.assertEqual(conn.execute.call_args.args[1], (drive.PROVEDOR, "novo-canal"))
