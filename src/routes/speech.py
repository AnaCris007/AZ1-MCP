from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Response

from az1_api.dependencies import get_speech_generator
from schemas.speech import SpeechErrorCode, SpeechRequest
from services.speech_service import (
    MAX_SPEECH_TEXT_LENGTH,
    GenerateSpeech,
    SpeechGenerationError,
    SpeechGenerationErrorCode,
)

router = APIRouter(tags=["speech"])


class SpeechAPIError(Exception):
    def __init__(self, status_code: int, error: SpeechErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    status_code: int
    error: SpeechErrorCode
    message: str


_ERROR_DETAILS = {
    SpeechGenerationErrorCode.EMPTY_TEXT: _HTTPErrorDetails(
        422, "empty_text", "O texto não pode estar vazio."
    ),
    SpeechGenerationErrorCode.TEXT_TOO_LONG: _HTTPErrorDetails(
        422, "text_too_long", f"O texto excede o limite de {MAX_SPEECH_TEXT_LENGTH} caracteres."
    ),
    SpeechGenerationErrorCode.PROVIDER_FAILED: _HTTPErrorDetails(
        502, "speech_generation_failed", "Não foi possível gerar o áudio. Tente novamente em instantes."
    ),
}


@router.post("/text-to-speech")
def text_to_speech(
    payload: SpeechRequest,
    generator: GenerateSpeech = Depends(get_speech_generator),
) -> Response:
    try:
        speech = generator.generate(payload.text, payload.voice)
    except SpeechGenerationError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise SpeechAPIError(details.status_code, details.error, details.message) from exc

    return Response(
        content=speech.content,
        media_type=speech.media_type,
        headers={"Content-Disposition": f'inline; filename="{speech.filename}"'},
    )

