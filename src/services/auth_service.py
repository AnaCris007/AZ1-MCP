from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import Any

import jwt

REQUIRED_AUDIENCE = "authenticated"
REQUIRED_PROVIDER = "azure"
ALGORITHMS_JWKS = ["ES256", "RS256"]
ALGORITHMS_SHARED_SECRET = ["HS256"]

KeyResolver = Callable[[str], Any]


class AuthMode(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class AuthKeyMode(StrEnum):
    JWKS = "jwks"
    SHARED_SECRET = "shared_secret"


@dataclass(frozen=True)
class SupabaseAuthSettings:
    project_url: str
    mode: AuthMode
    key_mode: AuthKeyMode = AuthKeyMode.JWKS
    shared_secret: str | None = None

    @property
    def issuer(self) -> str:
        return f"{self.project_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.project_url}/auth/v1/.well-known/jwks.json"

    @classmethod
    def from_environment(cls) -> SupabaseAuthSettings:
        mode = AuthMode(os.environ.get("AZ1_AUTH_MODE", AuthMode.ENABLED.value))
        if mode is AuthMode.DISABLED:
            return cls(project_url="", mode=mode)

        project_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if not project_url:
            raise RuntimeError(
                "SUPABASE_URL não configurada. Defina a URL do projeto Supabase "
                "(https://<project-ref>.supabase.co) ou use AZ1_AUTH_MODE=disabled em desenvolvimento."
            )

        key_mode = AuthKeyMode(os.environ.get("SUPABASE_AUTH_KEY_MODE", AuthKeyMode.JWKS.value))
        shared_secret = os.environ.get("SUPABASE_JWT_SECRET") or None
        if key_mode is AuthKeyMode.SHARED_SECRET and not shared_secret:
            raise RuntimeError("SUPABASE_AUTH_KEY_MODE=shared_secret exige SUPABASE_JWT_SECRET configurada.")

        return cls(project_url=project_url, mode=mode, key_mode=key_mode, shared_secret=shared_secret)


@dataclass(frozen=True)
class AuthenticatedUser:
    subject: str
    email: str
    name: str
    provider: str
    # Id em portfolio.usuario, ligado por ResolveOrCreateUsuario
    # (src/services/usuario_service.py). None quando a ligação falha ou o
    # banco está indisponível — a autenticação em si não depende disso.
    domain_user_id: int | None = None


class AuthErrorCode(Enum):
    MISSING = auto()
    MALFORMED = auto()
    EXPIRED = auto()
    INVALID_SIGNATURE = auto()
    INVALID_AUDIENCE = auto()
    INVALID_ISSUER = auto()
    INVALID_PROVIDER = auto()


class AuthError(Exception):
    def __init__(self, code: AuthErrorCode, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code.name)


def _default_key_resolver(settings: SupabaseAuthSettings) -> KeyResolver:
    if settings.key_mode is AuthKeyMode.SHARED_SECRET:
        secret = settings.shared_secret
        return lambda _token: secret

    jwk_client = jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)
    return lambda token: jwk_client.get_signing_key_from_jwt(token).key


class SupabaseTokenVerifier:
    """Valida o Bearer token emitido pelo Supabase Auth (RNF02).

    O `key_resolver` é injetável de propósito: é o que permite testar cada uma
    das cinco condições inválidas do RNF02 com um par de chaves local, sem
    depender do endpoint JWKS real do Supabase.
    """

    def __init__(self, settings: SupabaseAuthSettings, key_resolver: KeyResolver | None = None) -> None:
        self.settings = settings
        # Construído sob demanda: em AZ1_AUTH_MODE=disabled não há JWKS válido
        # (SUPABASE_URL fica vazia) e verify() nunca chega a ser chamado, então
        # criar o PyJWKClient no __init__ derrubaria a primeira requisição à toa.
        self._key_resolver = key_resolver

    def _resolve_key(self, token: str) -> Any:
        if self._key_resolver is None:
            self._key_resolver = _default_key_resolver(self.settings)
        return self._key_resolver(token)

    def verify(self, token: str) -> AuthenticatedUser:
        if not token or not token.strip():
            raise AuthError(AuthErrorCode.MISSING)

        algorithms = (
            ALGORITHMS_SHARED_SECRET if self.settings.key_mode is AuthKeyMode.SHARED_SECRET else ALGORITHMS_JWKS
        )

        try:
            signing_key = self._resolve_key(token)
        except jwt.exceptions.PyJWKClientError as exc:
            raise AuthError(AuthErrorCode.INVALID_SIGNATURE, str(exc)) from exc
        except jwt.exceptions.DecodeError as exc:
            raise AuthError(AuthErrorCode.MALFORMED, str(exc)) from exc

        try:
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=algorithms,
                audience=REQUIRED_AUDIENCE,
                issuer=self.settings.issuer,
                options={"require": ["exp", "sub"]},
            )
        except jwt.exceptions.ExpiredSignatureError as exc:
            raise AuthError(AuthErrorCode.EXPIRED, str(exc)) from exc
        except jwt.exceptions.InvalidAudienceError as exc:
            raise AuthError(AuthErrorCode.INVALID_AUDIENCE, str(exc)) from exc
        except jwt.exceptions.InvalidIssuerError as exc:
            raise AuthError(AuthErrorCode.INVALID_ISSUER, str(exc)) from exc
        except jwt.exceptions.InvalidSignatureError as exc:
            raise AuthError(AuthErrorCode.INVALID_SIGNATURE, str(exc)) from exc
        except jwt.exceptions.MissingRequiredClaimError as exc:
            raise AuthError(AuthErrorCode.MALFORMED, str(exc)) from exc
        except jwt.exceptions.DecodeError as exc:
            raise AuthError(AuthErrorCode.MALFORMED, str(exc)) from exc
        except jwt.exceptions.InvalidTokenError as exc:
            raise AuthError(AuthErrorCode.MALFORMED, str(exc)) from exc

        app_metadata = claims.get("app_metadata") or {}
        provider = app_metadata.get("provider", "")
        if provider != REQUIRED_PROVIDER:
            raise AuthError(AuthErrorCode.INVALID_PROVIDER, f"provider={provider!r}")

        user_metadata = claims.get("user_metadata") or {}
        email = claims.get("email") or user_metadata.get("email", "")
        name = user_metadata.get("full_name") or user_metadata.get("name") or email

        return AuthenticatedUser(subject=claims["sub"], email=email, name=name, provider=provider)
