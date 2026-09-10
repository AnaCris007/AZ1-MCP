import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import analysis_router, audio_router, chat_router, rag_router, transcription_router, webhooks_router
from routes.audio import AudioAPIError
from routes.chat import ChatAPIError
from routes.transcription import TranscriptionAPIError
from routes.webhooks import WebhookAPIError
from schemas.common import ErrorResponse

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="AZ1 API")
app.include_router(audio_router, prefix="/api/v1")
app.include_router(transcription_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")


# Fora do prefixo /api/v1 de propósito: quem consome é a infraestrutura
# (HEALTHCHECK do contêiner, balanceador, orquestrador), não o cliente da API, e
# esse contrato não deve mudar quando a versão da API mudar.
#
# Deliberadamente raso: responde "o processo subiu e atende HTTP". Não toca no
# MinIO, no Deepgram nem no Gemini — uma sonda que depende de terceiros faz o
# orquestrador reiniciar esta aplicação por causa de uma instabilidade que não é
# dela, trocando uma degradação parcial por uma indisponibilidade total.
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
