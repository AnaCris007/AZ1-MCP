import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import audio_router
from routes.audio import AudioAPIError
from schemas.audio import ErrorResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="AZ1 API")
app.include_router(audio_router, prefix="/api/v1")


@app.exception_handler(AudioAPIError)
def audio_api_error_handler(request: Request, exc: AudioAPIError) -> JSONResponse:
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
