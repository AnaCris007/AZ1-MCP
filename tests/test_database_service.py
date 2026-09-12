# Testes da camada de acesso ao banco relacional.
#
# O que mais importa aqui não é o pool, é a decisão de PAPEL. Conectar sem
# assumir `az1_app` significa conectar como dono, e dono **ignora as policies de
# RLS** — uma troca de postura de segurança que, se acontecer em silêncio,
# ninguém percebe. Por isso os testes prendem as duas pontas: que sem papel
# nenhum `SET ROLE` é emitido, e que com papel ele é emitido de fato.

from __future__ import annotations

import os
import unittest
from unittest import mock

from services.database_service import (
    BancoNaoConfigurado,
    PostgresSettings,
    _configurar_conexao,
    _identificador_seguro,
    criar_pool,
    verificar_conexao,
)

DSN_FALSA = "postgresql://usuario:senha@localhost:5432/az1"


def _conexao_falsa():
    conexao = mock.MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value
    return conexao, cursor


def _pool_falso(retorno):
    pool = mock.MagicMock()
    cursor = pool.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = retorno
    return pool


class TesteConfiguracao(unittest.TestCase):
    def test_sem_dsn_levanta_com_orientacao(self):
        with (
            mock.patch.dict(os.environ, {"SUPABASE_DB_URL": ""}, clear=False),
            self.assertRaises(BancoNaoConfigurado) as capturado,
        ):
            PostgresSettings.from_environment()
        self.assertIn("SUPABASE_DB_URL", str(capturado.exception))

    def test_dsn_ausente_e_dsn_vazia_sao_a_mesma_coisa(self):
        ambiente = {k: v for k, v in os.environ.items() if k != "SUPABASE_DB_URL"}
        with mock.patch.dict(os.environ, ambiente, clear=True), self.assertRaises(BancoNaoConfigurado):
            PostgresSettings.from_environment()

    def test_le_a_dsn_do_ambiente(self):
        with mock.patch.dict(os.environ, {"SUPABASE_DB_URL": DSN_FALSA}, clear=False):
            self.assertEqual(PostgresSettings.from_environment().dsn, DSN_FALSA)

    def test_sem_papel_definido_o_papel_e_none(self):
        # É o estado atual do projeto, enquanto não há autenticação: sem papel,
        # a conexão é a do dono e a RLS não se aplica.
        with mock.patch.dict(
            os.environ, {"SUPABASE_DB_URL": DSN_FALSA, "AZ1_DB_ROLE": ""}, clear=False
        ):
            self.assertIsNone(PostgresSettings.from_environment().papel)

    def test_papel_definido_e_lido(self):
        with mock.patch.dict(
            os.environ, {"SUPABASE_DB_URL": DSN_FALSA, "AZ1_DB_ROLE": "az1_app"}, clear=False
        ):
            self.assertEqual(PostgresSettings.from_environment().papel, "az1_app")


class TesteIdentificadorSeguro(unittest.TestCase):
    # `SET ROLE` não aceita parâmetro ligado, então o nome do papel entra no SQL
    # por interpolação. Esta validação é o que separa isso de uma injeção.
    def test_aceita_nome_valido(self):
        self.assertEqual(_identificador_seguro("az1_app"), "az1_app")

    def test_aceita_digitos_e_sublinhado(self):
        self.assertEqual(_identificador_seguro("papel_2"), "papel_2")

    def test_recusa_tentativa_de_injecao(self):
        for nome in ("az1; DROP TABLE portfolio.projeto", "a b", 'x"y', "pa-pel"):
            with self.assertRaises(ValueError):
                _identificador_seguro(nome)


class TesteConfiguracaoDaConexao(unittest.TestCase):
    def test_sem_papel_nao_emite_set_role(self):
        conexao, cursor = _conexao_falsa()
        _configurar_conexao(conexao, None)
        cursor.execute.assert_not_called()

    def test_com_papel_emite_set_role(self):
        conexao, cursor = _conexao_falsa()
        _configurar_conexao(conexao, "az1_app")
        cursor.execute.assert_called_once_with("SET ROLE az1_app")
        conexao.commit.assert_called_once()

    def test_papel_invalido_levanta_antes_de_tocar_o_banco(self):
        conexao, cursor = _conexao_falsa()
        with self.assertRaises(ValueError):
            _configurar_conexao(conexao, "az1; DROP TABLE x")
        cursor.execute.assert_not_called()


class TesteCriacaoDoPool(unittest.TestCase):
    def test_nao_abre_conexao_na_criacao(self):
        # Abrir na importação faria uma instalação sem banco deixar de subir a
        # API inteira, inclusive as rotas que não dependem de banco.
        pool = criar_pool(PostgresSettings(dsn=DSN_FALSA))
        self.addCleanup(pool.close)
        self.assertTrue(pool.closed)


class TesteVerificacaoDeConexao(unittest.TestCase):
    def test_verdadeiro_quando_o_banco_responde(self):
        self.assertTrue(verificar_conexao(_pool_falso((1,))))

    def test_falso_quando_a_resposta_nao_e_a_esperada(self):
        self.assertFalse(verificar_conexao(_pool_falso(None)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
