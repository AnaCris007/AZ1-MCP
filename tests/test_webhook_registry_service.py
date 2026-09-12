"""Regressões de falha SQL: toda conexão emprestada é devolvida uma vez."""
from datetime import UTC, datetime
from unittest import TestCase, mock

from services.webhook_registry_service import RegistroEventosPostgres
from services.webhook_service import EventoWebhook, SituacaoEvento


class TestCicloConexao(TestCase):
    def setUp(self):
        self.pool = mock.Mock()
        self.conn = self.pool.getconn.return_value
        self.registro = RegistroEventosPostgres(self.pool, "google_drive")
        self.evento = EventoWebhook(identificador="canal:1", tipo="drive.change", versao="1",
                                   marca_de_tempo=datetime.now(UTC), correlacao="canal", conteudo={})

    def test_falha_insert_devolve_conexao_e_desfaz_transacao(self):
        self.conn.execute.side_effect = RuntimeError("SQL indisponível")
        for _ in range(6):
            with self.assertRaises(RuntimeError):
                self.registro.reivindicar(self.evento)
        self.assertEqual(self.pool.putconn.call_count, 6)
        self.assertEqual(self.conn.rollback.call_count, 6)

    def test_falha_select_devolve_conexao(self):
        cursor = mock.Mock()
        cursor.fetchone.return_value = None
        self.conn.execute.side_effect = [cursor, RuntimeError("SELECT falhou")]
        with self.assertRaises(RuntimeError):
            self.registro.reivindicar(self.evento)
        self.pool.putconn.assert_called_once_with(self.conn)
        self.conn.rollback.assert_called_once()

    def test_falha_rollback_descarta_conexao(self):
        self.conn.execute.side_effect = RuntimeError("INSERT falhou")
        self.conn.rollback.side_effect = RuntimeError("conexão perdida")
        with self.assertRaisesRegex(RuntimeError, "INSERT falhou"):
            self.registro.reivindicar(self.evento)
        self.conn.close.assert_called_once()
        self.pool.putconn.assert_called_once_with(self.conn)

    def test_reivindicacao_mantem_conexao_ate_concluir(self):
        self.conn.execute.return_value.fetchone.return_value = (1,)
        reivindicacao = self.registro.reivindicar(self.evento)
        self.pool.putconn.assert_not_called()
        reivindicacao.concluir(SituacaoEvento.PROCESSADO)
        self.pool.putconn.assert_called_once_with(self.conn)

    def test_duplicata_devolve_uma_vez_mesmo_com_commit_falhando(self):
        self.conn.execute.return_value.fetchone.side_effect = [None, (datetime.now(UTC),)]
        self.conn.commit.side_effect = RuntimeError("commit falhou")
        with self.assertRaises(RuntimeError):
            self.registro.reivindicar(self.evento)
        self.pool.putconn.assert_called_once_with(self.conn)


class TestConfiguracaoWebhook(TestCase):
    def test_pool_separado_restrito_mesmo_sem_database_url(self):
        import os

        from az1_api.dependencies import get_webhook_connection_pool
        for ambiente, esperado in [({"SUPABASE_DB_URL": "postgresql://supabase/base"}, "postgresql://supabase/base"),
                                  ({"SUPABASE_DB_URL": "postgresql://supabase/base", "DATABASE_URL": "postgresql://postgres/base"}, "postgresql://postgres/base")]:
            get_webhook_connection_pool.cache_clear()
            with (mock.patch.dict(os.environ, ambiente, clear=True),
                  mock.patch("az1_api.dependencies.abrir_pool") as abrir):
                get_webhook_connection_pool()
                settings = abrir.call_args.args[0]
                self.assertEqual(settings.dsn, esperado)
                self.assertEqual(settings.papel, "az1_webhook")
        get_webhook_connection_pool.cache_clear()

    def test_cli_e_receptor_selecionam_a_mesma_base(self):
        import os

        from services.webhook_registry_service import PostgresSettings
        with mock.patch.dict(os.environ, {"DATABASE_URL": "", "SUPABASE_DB_URL": "postgresql://supabase/base"}, clear=True):
            self.assertEqual(PostgresSettings.from_environment().dsn, "postgresql://supabase/base")
