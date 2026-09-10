from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_alerta_desativador, get_alerta_listador, get_alerta_registrador
from az1_api.main import app
from services.alerta_service import AlertaServiceError, AlertaServiceErrorCode, AssinanteCriado, AssinantePublico


class FakeRegistrador:
    def __init__(self, result: AssinanteCriado | Exception) -> None:
        self.result = result

    def registrar(self, *, projeto_id: str, url: str) -> AssinanteCriado:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeDesativador:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def desativar(self, *, assinante_id: str) -> None:
        if self.error:
            raise self.error


class FakeListador:
    def __init__(self, assinantes: list[AssinantePublico]) -> None:
        self.assinantes = assinantes

    def listar(self) -> list[AssinantePublico]:
        return self.assinantes


class TestAlertaAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_registrar(self, result: AssinanteCriado | Exception) -> TestClient:
        app.dependency_overrides[get_alerta_registrador] = lambda: FakeRegistrador(result)
        return TestClient(app, raise_server_exceptions=False)

    def _client_desativar(self, error: Exception | None = None) -> TestClient:
        app.dependency_overrides[get_alerta_desativador] = lambda: FakeDesativador(error)
        return TestClient(app, raise_server_exceptions=False)

    def _client_listar(self, assinantes: list[AssinantePublico]) -> TestClient:
        app.dependency_overrides[get_alerta_listador] = lambda: FakeListador(assinantes)
        return TestClient(app, raise_server_exceptions=False)

    def test_cria_assinante_com_sucesso_e_retorna_secret(self) -> None:
        criado = AssinanteCriado(
            id="uuid-1",
            projeto_id="SYN-01",
            url="https://exemplo.com/webhook",
            secret="s3cr3t_t0k3n",
        )
        client = self._client_registrar(criado)

        response = client.post(
            "/api/v1/alertas/assinantes",
            json={"projeto_id": "SYN-01", "url": "https://exemplo.com/webhook"},
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["id"], "uuid-1")
        self.assertEqual(body["secret"], "s3cr3t_t0k3n")

    def test_url_sem_https_retorna_422(self) -> None:
        criado = AssinanteCriado(id="x", projeto_id="SYN-01", url="http://bad.com", secret="s")
        client = self._client_registrar(criado)

        response = client.post(
            "/api/v1/alertas/assinantes",
            json={"projeto_id": "SYN-01", "url": "http://sem-https.com/hook"},
        )

        self.assertEqual(response.status_code, 422)

    def test_get_assinantes_nao_expoe_secret(self) -> None:
        assinante = AssinantePublico(
            id="uuid-1",
            projeto_id="SYN-01",
            url="https://exemplo.com/webhook",
            ativa=True,
            criado_em="2026-09-10T10:00:00+00:00",
        )
        client = self._client_listar([assinante])

        response = client.get("/api/v1/alertas/assinantes")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("assinantes", body)
        primeiro = body["assinantes"][0]
        self.assertNotIn("secret", primeiro)
        self.assertNotIn("secret_hash", primeiro)
        self.assertEqual(primeiro["id"], "uuid-1")

    def test_desativar_assinante_com_sucesso(self) -> None:
        client = self._client_desativar()

        response = client.patch("/api/v1/alertas/assinantes/uuid-1/desativar")

        self.assertEqual(response.status_code, 200)

    def test_desativar_assinante_inexistente_retorna_404(self) -> None:
        client = self._client_desativar(
            error=AlertaServiceError(AlertaServiceErrorCode.ASSINANTE_NAO_ENCONTRADO)
        )

        response = client.patch("/api/v1/alertas/assinantes/nao-existe/desativar")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "assinante_nao_encontrado")


if __name__ == "__main__":
    unittest.main()
