import dataclasses
import logging
import os
from functools import lru_cache

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import ConnectionPool

from services.analysis_service import AnalyzeAudio
from services.audio_service import ReceiveAudio
from services.auth_service import (
    AuthenticatedUser,
    AuthError,
    AuthMode,
    SupabaseAuthSettings,
    SupabaseTokenVerifier,
)
from services.chat_service import AnswerChatMessage
from services.gemini_service import GeminiChatModel, GeminiSettings
from services.gemini_speech_service import DEFAULT_TTS_MODEL, GeminiSpeechModel
from services.speech_service import GenerateSpeech
from services.storage_service import S3AudioStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio
from services.usuario_service import ResolveOrCreateUsuario

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_DEV_MODE_USER = AuthenticatedUser(
    subject="dev-mode",
    email="dev@local",
    name="Usuário de desenvolvimento (AZ1_AUTH_MODE=disabled)",
    provider="disabled",
)


class AuthAPIError(Exception):
    """Erro HTTP de autenticação. O corpo é fixo (RNF02): não varia com a causa,
    para não funcionar como oráculo para quem está testando credenciais."""

    status_code = 401
    error = "unauthorized"
    message = "Token de autenticação ausente ou inválido."


@lru_cache
def get_audio_receiver() -> ReceiveAudio:
    settings = S3StorageSettings.from_environment()
    return ReceiveAudio(storage=S3AudioStorage.from_settings(settings))


@lru_cache
def get_transcriber() -> TranscribeAudio:
    settings = S3StorageSettings.from_environment()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    return TranscribeAudio(
        fetcher=S3AudioStorage.from_settings(settings),
        api_key=api_key,
    )


@lru_cache
def get_analyzer() -> AnalyzeAudio:
    import sys

    import pln.classificador as _pln_mod
    from pln.caminhos import MODELO_PADRAO
    from pln.classificador import carregar_modelo

    # Modelos serializados via 'python -m pln.classificador' registram classes como
    # '__main__'; via loky/spawn registram como '__mp_main__'. O shim abaixo
    # resolve ambos para 'pln.classificador' durante a desserialização.
    _aliases = ("__main__", "__mp_main__")
    _saved = {k: sys.modules.get(k) for k in _aliases}
    for k in _aliases:
        sys.modules[k] = _pln_mod
    try:
        modelo = carregar_modelo(MODELO_PADRAO)
    finally:
        for k, v in _saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    return AnalyzeAudio(transcriber=get_transcriber(), modelo=modelo)


@lru_cache
def get_chat_answerer() -> AnswerChatMessage:
    settings = GeminiSettings.from_environment()
    return AnswerChatMessage(model=GeminiChatModel.from_settings(settings))


@lru_cache
def get_speech_generator() -> GenerateSpeech:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada para geração de áudio.")
    model = os.environ.get("GEMINI_TTS_MODEL", DEFAULT_TTS_MODEL)
    return GenerateSpeech(model=GeminiSpeechModel.from_api_key(api_key, model))


@lru_cache
def get_token_verifier() -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(SupabaseAuthSettings.from_environment())


@lru_cache
def get_usuario_resolver() -> ResolveOrCreateUsuario | None:
    # Best-effort de propósito: nada mais na API depende do banco relacional
    # hoje, então uma falha aqui não pode derrubar a autenticação inteira.
    # Ver ResolveOrCreateUsuario em src/services/usuario_service.py.
    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning(
            "SUPABASE_DB_URL não configurada: login não será ligado a portfolio.usuario."
        )
        return None
    try:
        pool = ConnectionPool(dsn, min_size=1, max_size=5, open=True)
    except Exception:
        logger.exception("Falha ao abrir o pool de SUPABASE_DB_URL; login não será ligado a portfolio.usuario.")
        return None
    return ResolveOrCreateUsuario(pool)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    verifier: SupabaseTokenVerifier = Depends(get_token_verifier),
    usuario_resolver: ResolveOrCreateUsuario | None = Depends(get_usuario_resolver),
) -> AuthenticatedUser:
    if verifier.settings.mode is AuthMode.DISABLED:
        return _DEV_MODE_USER

    if credentials is None:
        raise AuthAPIError()

    try:
        user = verifier.verify(credentials.credentials)
    except AuthError as exc:
        # A causa vai só para o log (RNF02 proíbe credenciais nos registros); o
        # corpo da resposta é sempre o mesmo, para não servir de oráculo.
        logger.warning("Falha de autenticação (%s): %s", exc.code.name, exc.detail)
        raise AuthAPIError() from exc

    if usuario_resolver is not None:
        try:
            domain_user = usuario_resolver.resolve(auth_user_id=user.subject, email=user.email, name=user.name)
            user = dataclasses.replace(user, domain_user_id=domain_user.id)
        except Exception:
            # Autenticação (RNF02) não depende de portfolio.usuario: uma falha
            # aqui não deve virar 401 nem 500 para quem só quer usar o agente.
            logger.exception("Não foi possível ligar %s a portfolio.usuario.", user.email)

    return user
