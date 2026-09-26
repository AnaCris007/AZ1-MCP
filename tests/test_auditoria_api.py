from __future__ import annotations

import dataclasses
import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_listador_auditoria, require_authenticated_user
from az1_api.main import app
from services.auditoria_service import MensagemRegistrada
from services.auth_service import AuthenticatedUser


class FakeListador:
    def __init__(self, registros: list[MensagemRegistrada]) -> None:
        self.registros = registros
        self.ultimo_limit: int | None = None

    def listar(self, *, limit: int = 50, desde=None) -> list[MensagemRegistrada]:
        self.ultimo_limit = limit
        return self.registros[:limit]



# As rotas de alertas e auditoria estão atrás do RNF02, como todas as demais de
# /api/v1 (ver `_auth_dependency` em src/az1_api/main.py). Sem substituir a
# autenticação, cada requisição destes testes construía o verificador de token
# de verdade e morria em `SUPABASE_URL não configurada` — 500 no lugar do código
# esperado, e nada na falha apontava para a autenticação.
# `perfil` importa aqui: a rota devolve `conteudo` de `auditoria.mensagem` sem
# filtro de dono — leitura administrativa, restrita a diretor e PMO. Um usuário
# sem perfil administrativo recebe 403, e é o que
# `test_perfil_comum_nao_le_a_trilha` verifica.
_TEST_USER = AuthenticatedUser(
    subject="test-user",
    email="teste@example.com",
    name="Usuário de Teste",
    provider="azure",
    domain_user_id=7,
    perfil="pmo",
)


class TestAuditoriaAPI(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_com(self, registros: list[MensagemRegistrada]) -> tuple[TestClient, FakeListador]:
        fake = FakeListador(registros)
        app.dependency_overrides[get_listador_auditoria] = lambda: fake
        return TestClient(app, raise_server_exceptions=False), fake

    def test_perfil_comum_nao_le_a_trilha(self) -> None:
        """Líder de projeto não lê a conversa dos outros.

        Antes da correção esta rota devolvia `conteudo` de até 100 mensagens de
        qualquer usuário para quem estivesse apenas autenticado.
        """
        client, fake = self._client_com([])
        app.dependency_overrides[require_authenticated_user] = lambda: dataclasses.replace(
            _TEST_USER, perfil="lider_projeto"
        )

        response = client.get("/api/v1/auditoria/consultas")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "forbidden")
        # E não chegou a consultar: a recusa vem antes do banco.
        self.assertIsNone(fake.ultimo_limit)

    def test_perfil_ausente_nao_le_a_trilha(self) -> None:
        """Sem ligação com portfolio.usuario, a dúvida recusa."""
        client, _ = self._client_com([])
        app.dependency_overrides[require_authenticated_user] = lambda: dataclasses.replace(
            _TEST_USER, domain_user_id=None, perfil=None
        )

        response = client.get("/api/v1/auditoria/consultas")

        self.assertEqual(response.status_code, 403)

    def test_diretor_le_a_trilha(self) -> None:
        client, _ = self._client_com([])
        app.dependency_overrides[require_authenticated_user] = lambda: dataclasses.replace(
            _TEST_USER, perfil="diretor"
        )

        response = client.get("/api/v1/auditoria/consultas")

        self.assertEqual(response.status_code, 200)

    def test_retorna_lista_vazia_quando_sem_registros(self) -> None:
        client, _ = self._client_com([])

        response = client.get("/api/v1/auditoria/consultas")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"consultas": []})

    def test_retorna_mensagens_existentes(self) -> None:
        registros = [
            MensagemRegistrada(
                id="id-1",
                conversa_id="conv-uuid-abc",
                papel="usuario",
                conteudo="Qual o status do projeto?",
                tempo_processamento_ms=None,
                criada_em="2026-09-10T10:00:00+00:00",
            ),
            MensagemRegistrada(
                id="id-2",
                conversa_id="conv-uuid-abc",
                papel="agente",
                conteudo="O projeto está em dia.",
                tempo_processamento_ms=350,
                criada_em="2026-09-10T10:00:01+00:00",
            ),
        ]
        client, _ = self._client_com(registros)

        response = client.get("/api/v1/auditoria/consultas")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["consultas"]), 2)
        self.assertEqual(body["consultas"][0]["papel"], "usuario")
        self.assertEqual(body["consultas"][1]["tempo_processamento_ms"], 350)

    def test_respeita_parametro_limit(self) -> None:
        registros = [
            MensagemRegistrada(
                id=f"id-{i}",
                conversa_id="conv-uuid",
                papel="usuario",
                conteudo=f"msg {i}",
                tempo_processamento_ms=None,
                criada_em="2026-09-10T10:00:00+00:00",
            )
            for i in range(10)
        ]
        client, fake = self._client_com(registros)

        response = client.get("/api/v1/auditoria/consultas?limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.ultimo_limit, 3)
        self.assertEqual(len(response.json()["consultas"]), 3)

    def test_limit_acima_de_100_retorna_422(self) -> None:
        client, _ = self._client_com([])

        response = client.get("/api/v1/auditoria/consultas?limit=101")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
