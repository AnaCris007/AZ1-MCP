# Testes do DSN do cliente vetorial.
#
# O que se protege aqui é uma linha que PARECE cosmética e não é. A `vecs` emite
# `set local ivfflat.probes = :probes` em toda busca, e o PostgreSQL não aceita
# parâmetro em `SET`: só funciona com um driver que interpole do lado do
# cliente, ou seja, psycopg2. Com psycopg3 a busca levanta `SyntaxError`, o chat
# cai no curto-circuito BASE_INDISPONIVEL e o agente recusa TODA pergunta.
#
# Já aconteceu, e não por mudança de código: `SQLAlchemy>=2.0` era piso sem
# teto, entrou o 2.1, e o 2.1 trocou o DBAPI padrão de `postgresql://`. Quem
# olhar `_com_driver_explicito` sem esse contexto vai querer simplificá-la.
#
# Nenhum caso aqui toca banco ou rede: o que se verifica é a forma do DSN.

from __future__ import annotations

import unittest
from unittest import mock

from rag import indexador


class TesteDriverDoClienteVetorial(unittest.TestCase):
    def test_dsn_do_supabase_recebe_o_psycopg2(self) -> None:
        url = "postgresql://postgres.abc:senha@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"

        resultado = indexador._com_driver_explicito(url)

        self.assertTrue(resultado.startswith("postgresql+psycopg2://"))
        # O resto do DSN passa intacto: usuário, senha, host, porta e banco.
        self.assertTrue(
            resultado.endswith("postgres.abc:senha@aws-0-sa-east-1.pooler.supabase.com:5432/postgres")
        )

    def test_forma_antiga_postgres_tambem_e_convertida(self) -> None:
        # O Supabase ainda emite `postgres://` em alguns lugares do painel, e o
        # SQLAlchemy recusa esse esquema desde a 1.4.
        resultado = indexador._com_driver_explicito("postgres://u:p@h:5432/db")

        self.assertEqual(resultado, "postgresql+psycopg2://u:p@h:5432/db")

    def test_dsn_que_ja_traz_o_driver_passa_intacto(self) -> None:
        url = "postgresql+psycopg2://u:p@h:5432/db"

        self.assertEqual(indexador._com_driver_explicito(url), url)

    def test_driver_explicito_de_outra_pessoa_e_respeitado(self) -> None:
        # Não sobrescrever: quem escreveu `+asyncpg` no DSN tinha um motivo, e
        # trocar por baixo seria pior do que falhar de forma visível.
        url = "postgresql+asyncpg://u:p@h:5432/db"

        self.assertEqual(indexador._com_driver_explicito(url), url)

    def test_esquema_desconhecido_nao_e_remendado(self) -> None:
        url = "mysql://u:p@h:3306/db"

        self.assertEqual(indexador._com_driver_explicito(url), url)

    def test_db_url_aplica_o_driver_ao_valor_do_ambiente(self) -> None:
        with mock.patch.dict(
            "os.environ", {"SUPABASE_DB_URL": "postgresql://u:p@h:5432/db"}, clear=False
        ):
            self.assertEqual(indexador._db_url(), "postgresql+psycopg2://u:p@h:5432/db")

    def test_db_url_sem_variavel_continua_explicando_o_que_falta(self) -> None:
        with (
            mock.patch.dict("os.environ", {"SUPABASE_DB_URL": ""}, clear=False),
            self.assertRaises(RuntimeError) as contexto,
        ):
            indexador._db_url()

        self.assertIn("SUPABASE_DB_URL", str(contexto.exception))


class TesteDimensaoVemDeUmaFonteSo(unittest.TestCase):
    def test_indexador_nao_declara_a_propria_dimensao(self) -> None:
        """A dimensão é importada do `embedder`, não redeclarada.

        Duas constantes divergem em silêncio: a coleção aceitaria vetor de
        tamanho diferente do que o modelo produz, e o erro só apareceria no
        upsert — depois de a carga já ter começado.
        """
        from rag.embedder import DIMENSAO_EMBEDDING

        self.assertIs(indexador.DIMENSAO_EMBEDDING, DIMENSAO_EMBEDDING)


if __name__ == "__main__":
    unittest.main()
