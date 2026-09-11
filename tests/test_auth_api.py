from __future__ import annotations

import time
import unittest

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from az1_api.dependencies import get_chat_answerer, get_token_verifier
from az1_api.main import app
from services.auth_service import (
    REQUIRED_AUDIENCE,
    AuthKeyMode,
    AuthMode,
    SupabaseAuthSettings,
    SupabaseTokenVerifier,
)
from services.chat_service import ChatReply

_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1()).private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
_OTHER_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1()).private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
_PUBLIC_KEY = serialization.load_pem_private_key(_PRIVATE_KEY, password=None).public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
)

_SETTINGS = SupabaseAuthSettings(
    project_url="https://projeto-teste.supabase.co",
    mode=AuthMode.ENABLED,
    key_mode=AuthKeyMode.JWKS,
)


def _make_valid_token() -> str:
    now = int(time.time())
    claims = {
        "aud": REQUIRED_AUDIENCE,
        "iss": _SETTINGS.issuer,
        "sub": "11111111-1111-1111-1111-111111111111",
        "exp": now + 3600,
        "email": "ana.jardim@sou.inteli.edu.br",
        "app_metadata": {"provider": "azure"},
        "user_metadata": {"full_name": "Ana Jardim"},
    }
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256")


class FakeAnswerer:
    """Espiona se a regra de negócio chegou a ser executada."""

    def __init__(self) -> None:
        self.foi_chamado = False

    def answer(self, message: str, conversation_id: str | None = None) -> ChatReply:
        self.foi_chamado = True
        return ChatReply(text="resposta")


_UNAUTHORIZED_BODY = {
    "error": "unauthorized",
    "message": "Token de autenticação ausente ou inválido.",
}


class TestAuthAPI(unittest.TestCase):
    """Evidência do RNF02: as cinco condições inválidas rejeitam com 401,
    antes de qualquer regra de negócio, sem variar a mensagem nem vazar a
    credencial para o log."""

    def setUp(self) -> None:
        self.answerer = FakeAnswerer()
        app.dependency_overrides[get_chat_answerer] = lambda: self.answerer
        app.dependency_overrides[get_token_verifier] = lambda: SupabaseTokenVerifier(
            _SETTINGS, key_resolver=lambda _token: _PUBLIC_KEY
        )
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _post_chat(self, headers: dict[str, str] | None = None, json: dict | None = None):
        return self.client.post(
            "/api/v1/chat",
            json=json if json is not None else {"message": "Oi", "conversation_id": "conv_1"},
            headers=headers,
        )

    def test_aceita_token_valido_e_executa_a_regra_de_negocio(self) -> None:
        response = self._post_chat(headers={"Authorization": f"Bearer {_make_valid_token()}"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.answerer.foi_chamado)

    def test_rejeita_credencial_ausente(self) -> None:
        response = self._post_chat()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        self.assertFalse(self.answerer.foi_chamado)
        self.assertEqual(response.headers.get("www-authenticate"), "Bearer")

    def test_rejeita_credencial_malformada(self) -> None:
        response = self._post_chat(headers={"Authorization": "Bearer isto-nao-e-um-jwt"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        self.assertFalse(self.answerer.foi_chamado)

    def test_rejeita_credencial_expirada(self) -> None:
        now = int(time.time())
        claims = {
            "aud": REQUIRED_AUDIENCE,
            "iss": _SETTINGS.issuer,
            "sub": "u1",
            "exp": now - 10,
            "app_metadata": {"provider": "azure"},
        }
        expirado = jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256")

        response = self._post_chat(headers={"Authorization": f"Bearer {expirado}"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        self.assertFalse(self.answerer.foi_chamado)

    def test_rejeita_assinatura_invalida(self) -> None:
        now = int(time.time())
        claims = {
            "aud": REQUIRED_AUDIENCE,
            "iss": _SETTINGS.issuer,
            "sub": "u1",
            "exp": now + 3600,
            "app_metadata": {"provider": "azure"},
        }
        assinado_com_outra_chave = jwt.encode(claims, _OTHER_PRIVATE_KEY, algorithm="ES256")

        response = self._post_chat(headers={"Authorization": f"Bearer {assinado_com_outra_chave}"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        self.assertFalse(self.answerer.foi_chamado)

    def test_rejeita_audiencia_incorreta(self) -> None:
        now = int(time.time())
        claims = {
            "aud": "outro-publico",
            "iss": _SETTINGS.issuer,
            "sub": "u1",
            "exp": now + 3600,
            "app_metadata": {"provider": "azure"},
        }
        token = jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256")

        response = self._post_chat(headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        self.assertFalse(self.answerer.foi_chamado)

    def test_401_vence_422_quando_corpo_tambem_e_invalido(self) -> None:
        # Dependências de rota resolvem antes da validação do corpo: mesmo com
        # payload incompleto, a ausência de credencial deve vencer como 401,
        # nunca 422 — é o que prova "antes de qualquer regra de negócio".
        response = self._post_chat(json={})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.answerer.foi_chamado)

    def test_causa_da_falha_nao_aparece_no_corpo_nem_credencial_no_log(self) -> None:
        token_malformado = "Bearer isto-nao-e-um-jwt"

        with self.assertLogs("az1_api.dependencies", level="WARNING") as ctx:
            response = self._post_chat(headers={"Authorization": token_malformado})

        # A mensagem ao cliente não varia com a causa...
        self.assertEqual(response.json(), _UNAUTHORIZED_BODY)
        # ...mas a causa fica registrada para operação, sem a credencial em si.
        log_output = "\n".join(ctx.output)
        self.assertIn("MALFORMED", log_output)
        self.assertNotIn("isto-nao-e-um-jwt", log_output)

    def test_health_nao_exige_credencial(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)


class TestAuthModeDisabled(unittest.TestCase):
    """AZ1_AUTH_MODE=disabled é a válvula de desenvolvimento (não deve
    funcionar em produção — ver docker/api/entrypoint.sh)."""

    def setUp(self) -> None:
        self.answerer = FakeAnswerer()
        app.dependency_overrides[get_chat_answerer] = lambda: self.answerer
        app.dependency_overrides[get_token_verifier] = lambda: SupabaseTokenVerifier(
            SupabaseAuthSettings(project_url="", mode=AuthMode.DISABLED)
        )
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_libera_acesso_sem_credencial(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Oi", "conversation_id": "conv_1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.answerer.foi_chamado)


if __name__ == "__main__":
    unittest.main()
