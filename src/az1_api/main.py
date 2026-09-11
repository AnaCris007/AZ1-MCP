import logging
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import ConnectionPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from az1_api.dependencies import (
    AuthAPIError,
    get_connection_pool,
    require_authenticated_user,
)
from routes import (
    alerta_router,
    analysis_router,
    audio_router,
    auditoria_router,
    chat_router,
    portfolio_router,
    rag_router,
    speech_router,
    transcription_router,
    webhooks_router,
)
from routes.alerta import AlertaAPIError
from routes.audio import AudioAPIError
from routes.auditoria import AuditoriaAPIError
from routes.chat import ChatAPIError
from routes.portfolio import PortfolioAPIError
from routes.speech import SpeechAPIError
from routes.transcription import TranscriptionAPIError
from routes.webhooks import WebhookAPIError
from schemas.common import ErrorResponse
from services.database_service import BancoNaoConfigurado, verificar_conexao

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="AZ1 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# RNF02: toda funcionalidade protegida exige sessão/token válido de um
# provedor SSO, rejeitado com 401 antes de qualquer regra de negócio. /health
# fica de fora de propósito — o RNF07 depende de sondá-lo sem credencial.
_auth_dependency = [Depends(require_authenticated_user)]
app.include_router(audio_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(transcription_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(analysis_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(chat_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(rag_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(portfolio_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(speech_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(alerta_router, prefix="/api/v1", dependencies=_auth_dependency)
app.include_router(auditoria_router, prefix="/api/v1", dependencies=_auth_dependency)

# Webhooks ficam fora do RNF02: quem chama é o provedor (Google Drive /
# Microsoft Graph), que não tem token do SSO. A autenticidade dessas entregas
# vem do segredo compartilhado verificado em src/services/webhook_*.
app.include_router(webhooks_router, prefix="/api/v1")


# Deliberadamente raso: não toca banco, MinIO, Deepgram nem Gemini. O RNF07
# exige HTTP 200 em até dois segundos, e checar dependência externa aqui faria o
# próprio requisito depender da latência de terceiros. Quem verifica dependência
# é `/health/ready`, abaixo.
@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Prontidão, separada da vivacidade. Responde 503 quando o banco não está
# utilizável.
#
# O pool chega por `Depends`, e não por chamada direta a `get_connection_pool()`:
# chamada direta ignora `app.dependency_overrides` e deixa a rota intestável sem
# um Supabase de verdade.
#
# Banco não configurado sai daqui como `BancoNaoConfigurado` e é convertido em
# 503 pelo manipulador registrado no fim deste módulo — indisponibilidade do
# ponto de vista de quem chama, não erro de programação.
@app.get("/health/ready", tags=["infra"])
def health_ready(pool: Annotated[ConnectionPool, Depends(get_connection_pool)]) -> JSONResponse:
    try:
        pronto = verificar_conexao(pool)
    except Exception as erro:  # noqa: BLE001 — qualquer falha de conexão é indisponibilidade
        return JSONResponse(
            status_code=503,
            content={"status": "indisponivel", "motivo": f"{type(erro).__name__}: {erro}"},
        )

    if not pronto:
        return JSONResponse(status_code=503, content={"status": "indisponivel"})
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.exception_handler(AlertaAPIError)
def alerta_api_error_handler(request: Request, exc: AlertaAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(AuditoriaAPIError)
def auditoria_api_error_handler(request: Request, exc: AuditoriaAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(TranscriptionAPIError)
def transcription_api_error_handler(request: Request, exc: TranscriptionAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(AudioAPIError)
def audio_api_error_handler(request: Request, exc: AudioAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(PortfolioAPIError)
def portfolio_api_error_handler(request: Request, exc: PortfolioAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(ChatAPIError)
def chat_api_error_handler(request: Request, exc: ChatAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(SpeechAPIError)
def speech_api_error_handler(request: Request, exc: SpeechAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(AuthAPIError)
def auth_api_error_handler(request: Request, exc: AuthAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(WebhookAPIError)
def webhook_api_error_handler(request: Request, exc: WebhookAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


# Banco ausente é indisponibilidade de dependência, não defeito de programação:
# precisa sair como 503, e não pelo manipulador genérico de 500 abaixo. Vale
# para os endpoints cuja razão de existir É o banco — alertas e auditoria. Os
# efeitos colaterais de /chat e /analyze não chegam aqui: degradam nos próprios
# provedores, ver `dependencies.get_conversa_repository`.
@app.exception_handler(BancoNaoConfigurado)
def banco_nao_configurado_handler(request: Request, exc: BancoNaoConfigurado) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(error="service_unavailable", message=str(exc)).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 400:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error="bad_request", message=str(exc.detail)).model_dump(),
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado ao processar %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="internal_error", message="Erro interno inesperado.").model_dump(),
    )
