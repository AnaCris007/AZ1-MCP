from __future__ import annotations

import unittest

from services.usuario_service import DEFAULT_PERFIL, DomainUser, ResolveOrCreateUsuario


class FakeCursor:
    def __init__(self, results: list[tuple | None]) -> None:
        self._results = list(results)
        self.queries: list[tuple[str, tuple]] = []

    def execute(self, query: str, params: tuple = ()) -> None:
        self.queries.append((query, params))

    def fetchone(self) -> tuple | None:
        return self._results.pop(0) if self._results else None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def connection(self) -> FakeConnection:
        return self._connection


class TestResolveOrCreateUsuario(unittest.TestCase):
    def test_encontra_por_auth_user_id_sem_escrever_no_banco(self) -> None:
        cursor = FakeCursor(results=[(42, "diretor")])
        conn = FakeConnection(cursor)
        resolver = ResolveOrCreateUsuario(FakePool(conn))

        result = resolver.resolve(auth_user_id="uuid-1", email="robson.oliveira@metro.example", name="Robson")

        self.assertEqual(result, DomainUser(id=42, perfil="diretor"))
        self.assertEqual(len(cursor.queries), 1)
        self.assertEqual(conn.commits, 0)

    def test_encontra_por_email_e_liga_o_auth_user_id(self) -> None:
        cursor = FakeCursor(results=[None, (7, "pmo")])
        conn = FakeConnection(cursor)
        resolver = ResolveOrCreateUsuario(FakePool(conn))

        result = resolver.resolve(auth_user_id="uuid-2", email="Maria.Santos@Metro.Example", name="Maria")

        self.assertEqual(result, DomainUser(id=7, perfil="pmo"))
        self.assertEqual(len(cursor.queries), 3)  # select por auth_user_id, select por email, update
        self.assertEqual(conn.commits, 1)

        update_query, update_params = cursor.queries[2]
        self.assertIn("UPDATE portfolio.usuario", update_query)
        self.assertEqual(update_params, ("uuid-2", 7))

        # e-mail normalizado para minúsculas antes de comparar
        _, select_email_params = cursor.queries[1]
        self.assertEqual(select_email_params, ("maria.santos@metro.example",))

    def test_cria_usuario_novo_quando_nao_encontra_nenhuma_correspondencia(self) -> None:
        cursor = FakeCursor(results=[None, None, (99, DEFAULT_PERFIL)])
        conn = FakeConnection(cursor)
        resolver = ResolveOrCreateUsuario(FakePool(conn))

        result = resolver.resolve(auth_user_id="uuid-3", email="ana.jardim@sou.inteli.edu.br", name="Ana Jardim")

        self.assertEqual(result, DomainUser(id=99, perfil=DEFAULT_PERFIL))
        self.assertEqual(len(cursor.queries), 3)  # select por auth_user_id, select por email, insert
        self.assertEqual(conn.commits, 1)

        insert_query, insert_params = cursor.queries[2]
        self.assertIn("INSERT INTO portfolio.usuario", insert_query)
        self.assertEqual(insert_params, ("uuid-3", "Ana Jardim", "ana.jardim@sou.inteli.edu.br", DEFAULT_PERFIL))

    def test_usa_email_como_nome_quando_nome_vem_vazio(self) -> None:
        cursor = FakeCursor(results=[None, None, (100, DEFAULT_PERFIL)])
        conn = FakeConnection(cursor)
        resolver = ResolveOrCreateUsuario(FakePool(conn))

        resolver.resolve(auth_user_id="uuid-4", email="sem.nome@sou.inteli.edu.br", name="   ")

        _, insert_params = cursor.queries[2]
        self.assertEqual(insert_params[1], "sem.nome@sou.inteli.edu.br")


if __name__ == "__main__":
    unittest.main()
