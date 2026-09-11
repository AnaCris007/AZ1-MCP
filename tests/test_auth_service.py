from __future__ import annotations

import os
import time
import unittest
from unittest import mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from services.auth_service import (
    REQUIRED_AUDIENCE,
    AuthError,
    AuthErrorCode,
    AuthKeyMode,
    AuthMode,
    SupabaseAuthSettings,
    SupabaseTokenVerifier,
)


def _generate_key_pair() -> tuple[bytes, bytes]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


_TRUSTED_PRIVATE_KEY, _TRUSTED_PUBLIC_KEY = _generate_key_pair()
_OTHER_PRIVATE_KEY, _OTHER_PUBLIC_KEY = _generate_key_pair()

_SETTINGS = SupabaseAuthSettings(
    project_url="https://projeto-teste.supabase.co",
    mode=AuthMode.ENABLED,
    key_mode=AuthKeyMode.JWKS,
)


def _make_token(private_key: bytes = _TRUSTED_PRIVATE_KEY, **claim_overrides: object) -> str:
    now = int(time.time())
    claims = {
        "aud": REQUIRED_AUDIENCE,
        "iss": _SETTINGS.issuer,
        "sub": "11111111-1111-1111-1111-111111111111",
        "exp": now + 3600,
        "iat": now,
        "email": "ana.jardim@sou.inteli.edu.br",
        "app_metadata": {"provider": "azure"},
        "user_metadata": {"full_name": "Ana Jardim"},
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, private_key, algorithm="ES256")


class TestSupabaseTokenVerifier(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = SupabaseTokenVerifier(_SETTINGS, key_resolver=lambda _token: _TRUSTED_PUBLIC_KEY)

    def test_aceita_token_valido_e_extrai_o_usuario(self) -> None:
        user = self.verifier.verify(_make_token())

        self.assertEqual(user.subject, "11111111-1111-1111-1111-111111111111")
        self.assertEqual(user.email, "ana.jardim@sou.inteli.edu.br")
        self.assertEqual(user.name, "Ana Jardim")
        self.assertEqual(user.provider, "azure")

    def test_rejeita_token_ausente(self) -> None:
        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify("")

        self.assertEqual(ctx.exception.code, AuthErrorCode.MISSING)

    def test_rejeita_token_malformado(self) -> None:
        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify("isto-nao-e-um-jwt")

        self.assertEqual(ctx.exception.code, AuthErrorCode.MALFORMED)

    def test_rejeita_token_expirado(self) -> None:
        expirado = _make_token(exp=int(time.time()) - 10)

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(expirado)

        self.assertEqual(ctx.exception.code, AuthErrorCode.EXPIRED)

    def test_rejeita_assinatura_invalida(self) -> None:
        assinado_com_outra_chave = _make_token(private_key=_OTHER_PRIVATE_KEY)

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(assinado_com_outra_chave)

        self.assertEqual(ctx.exception.code, AuthErrorCode.INVALID_SIGNATURE)

    def test_rejeita_audiencia_incorreta(self) -> None:
        audiencia_errada = _make_token(aud="outro-publico")

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(audiencia_errada)

        self.assertEqual(ctx.exception.code, AuthErrorCode.INVALID_AUDIENCE)

    def test_rejeita_issuer_de_outro_projeto_supabase(self) -> None:
        # O aud de todo JWT do Supabase é a mesma string "authenticated" — quem
        # isola um projeto do outro é o issuer, por isso este caso é
        # verificado separadamente da audiência incorreta.
        outro_projeto = _make_token(iss="https://outro-projeto.supabase.co/auth/v1")

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(outro_projeto)

        self.assertEqual(ctx.exception.code, AuthErrorCode.INVALID_ISSUER)

    def test_rejeita_provider_diferente_de_azure(self) -> None:
        cadastro_por_email = _make_token(app_metadata={"provider": "email"})

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(cadastro_por_email)

        self.assertEqual(ctx.exception.code, AuthErrorCode.INVALID_PROVIDER)

    def test_rejeita_token_sem_claim_sub(self) -> None:
        now = int(time.time())
        payload = {
            "aud": REQUIRED_AUDIENCE,
            "iss": _SETTINGS.issuer,
            "exp": now + 3600,
            "app_metadata": {"provider": "azure"},
        }
        token = jwt.encode(payload, _TRUSTED_PRIVATE_KEY, algorithm="ES256")

        with self.assertRaises(AuthError) as ctx:
            self.verifier.verify(token)

        self.assertEqual(ctx.exception.code, AuthErrorCode.MALFORMED)


class TestSupabaseAuthSettingsFromEnvironment(unittest.TestCase):
    def test_modo_disabled_nao_exige_supabase_url(self) -> None:
        with mock.patch.dict(os.environ, {"AZ1_AUTH_MODE": "disabled"}, clear=True):
            settings = SupabaseAuthSettings.from_environment()

        self.assertEqual(settings.mode, AuthMode.DISABLED)

    def test_modo_enabled_sem_supabase_url_levanta_erro_de_configuracao(self) -> None:
        with mock.patch.dict(os.environ, {"AZ1_AUTH_MODE": "enabled"}, clear=True), self.assertRaises(RuntimeError):
            SupabaseAuthSettings.from_environment()

    def test_le_supabase_url_e_remove_barra_final(self) -> None:
        env = {"AZ1_AUTH_MODE": "enabled", "SUPABASE_URL": "https://projeto.supabase.co/"}
        with mock.patch.dict(os.environ, env, clear=True):
            settings = SupabaseAuthSettings.from_environment()

        self.assertEqual(settings.project_url, "https://projeto.supabase.co")
        self.assertEqual(settings.key_mode, AuthKeyMode.JWKS)

    def test_modo_shared_secret_sem_segredo_levanta_erro_de_configuracao(self) -> None:
        env = {
            "AZ1_AUTH_MODE": "enabled",
            "SUPABASE_URL": "https://projeto.supabase.co",
            "SUPABASE_AUTH_KEY_MODE": "shared_secret",
        }
        with mock.patch.dict(os.environ, env, clear=True), self.assertRaises(RuntimeError):
            SupabaseAuthSettings.from_environment()


if __name__ == "__main__":
    unittest.main()
