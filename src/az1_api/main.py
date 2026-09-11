import logging

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from az1_api.dependencies import AuthAPIError, require_authenticated_user
from routes import (
    analysis_router,
    audio_router,
    chat_router,
    rag_router,
    speech_router,
    transcription_router,
    webhooks_router,
)
from routes.audio import AudioAPIError
from routes.chat import ChatAPIError
from routes.speech import SpeechAPIError
from routes.transcription import TranscriptionAPIError
from routes.webhooks import WebhookAPIError
from schemas.common import ErrorResponse

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
app.include_router(speech_router, prefix="/api/v1", dependencies=_auth_dependency)

# Webhooks ficam fora do RNF02: quem chama é o provedor (Google Drive /
# Microsoft Graph), que não tem token do SSO. A autenticidade dessas entregas
# vem do segredo compartilhado verificado em src/services/webhook_*.
app.include_router(webhooks_router, prefix="/api/v1")


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}


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
