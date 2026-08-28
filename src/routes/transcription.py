from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Query

from az1_api.dependencies import get_transcriber
from schemas.transcription import (
    TranscriptionErrorCode,
    TranscriptionLanguage,
    TranscriptionResponse,
)
from services.transcription_service import TranscribeAudio, TranscriptionError
from services.transcription_service import TranscriptionErrorCode as SvcErrorCode

router = APIRouter(tags=["transcription"])


class TranscriptionAPIError(Exception):
    def __init__(self, status_code: int, error: TranscriptionErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    status_code: int
    error: TranscriptionErrorCode
    message: str


_ERROR_DETAILS = {
    SvcErrorCode.AUDIO_NOT_FOUND: _HTTPErrorDetails(
        404,
        "audio_not_found",
        "Áudio não encontrado. O id informado não existe ou já expirou.",
    ),
    SvcErrorCode.TRANSCRIPTION_FAILED: _HTTPErrorDetails(
        502,
        "transcription_failed",
        "Falha ao transcrever o áudio. Tente novamente em instantes.",
    ),
}


@router.post("/audio/{audio_id}/transcribe", response_model=TranscriptionResponse, status_code=200)
async def transcribe_audio(
    audio_id: str,
    language: TranscriptionLanguage = Query(
        default="pt-BR",
        description="Idioma do áudio. Nesta versão, apenas pt-BR é suportado.",
    ),
    transcriber: TranscribeAudio = Depends(get_transcriber),
) -> TranscriptionResponse:
    try:
        result = await transcriber.transcribe(audio_id=audio_id, language=language)
    except TranscriptionError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise TranscriptionAPIError(details.status_code, details.error, details.message) from exc

    return TranscriptionResponse(
        audio_id=audio_id,
        text=result.text,
        language=result.language,
        confidence=result.confidence,
        duration_seconds=result.duration_seconds,
    )
