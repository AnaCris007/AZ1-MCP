# Testes de EventoLocalRepository: pool e cursor mockados, sem Postgres real,
# mesmo padrão de test_database_service.py.

from __future__ import annotations

import unittest
from datetime import date, time
from unittest import mock

from services.evento_local_repository import EventoLocalRepository


def _pool_com_cursor():
    pool = mock.MagicMock()
    cursor = pool.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    return pool, cursor


class TestEventoLocalRepository(unittest.TestCase):
    def test_criar_devolve_os_campos_ecoados_pelo_banco(self):
        pool, cursor = _pool_com_cursor()
        cursor.fetchone.return_value = (7, "Reunião de time", date(2026, 12, 5), time(9, 0), "Alinhamento semanal")
        repositorio = EventoLocalRepository(pool)

        evento = repositorio.criar(
            usuario_id=1, titulo="Reunião de time", data=date(2026, 12, 5),
            hora=time(9, 0), descricao="Alinhamento semanal",
        )

        self.assertEqual(evento.id, 7)
        self.assertEqual(evento.hora, time(9, 0))
        sql, parametros = cursor.execute.call_args.args
        self.assertIn("INSERT INTO portfolio.evento_local", sql)
        self.assertEqual(parametros, (1, "Reunião de time", date(2026, 12, 5), time(9, 0), "Alinhamento semanal"))

    def test_criar_sem_hora_nao_fabrica_horario(self):
        pool, cursor = _pool_com_cursor()
        cursor.fetchone.return_value = (7, "Dia inteiro", date(2026, 12, 5), None, "")
        repositorio = EventoLocalRepository(pool)

        evento = repositorio.criar(usuario_id=1, titulo="Dia inteiro", data=date(2026, 12, 5), hora=None, descricao="")

        self.assertIsNone(evento.hora)

    def test_listar_filtra_por_usuario_no_sql(self):
        pool, cursor = _pool_com_cursor()
        cursor.fetchall.return_value = [(1, "Evento", date(2026, 12, 5), None, "")]
        repositorio = EventoLocalRepository(pool)

        eventos = repositorio.listar(42)

        self.assertEqual(len(eventos), 1)
        sql, parametros = cursor.execute.call_args.args
        self.assertIn("WHERE usuario_id = %s", sql)
        self.assertEqual(parametros, (42,))

    def test_apagar_evento_proprio_devolve_true(self):
        pool, cursor = _pool_com_cursor()
        cursor.fetchone.return_value = (7,)
        repositorio = EventoLocalRepository(pool)

        self.assertTrue(repositorio.apagar(usuario_id=1, evento_id=7))
        sql, parametros = cursor.execute.call_args.args
        self.assertIn("AND usuario_id = %s", sql)
        self.assertEqual(parametros, (7, 1))

    def test_apagar_evento_de_outra_pessoa_devolve_false_sem_apagar(self):
        pool, cursor = _pool_com_cursor()
        cursor.fetchone.return_value = None
        repositorio = EventoLocalRepository(pool)

        self.assertFalse(repositorio.apagar(usuario_id=2, evento_id=7))


if __name__ == "__main__":
    unittest.main(verbosity=2)
