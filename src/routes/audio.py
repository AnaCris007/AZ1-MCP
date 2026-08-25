from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, File, UploadFile

from az1_api.dependencies import get_audio_receiver
from schemas.audio import AudioErrorCode, AudioUploadResponse
from services.audio_service import AudioReceptionError, AudioReceptionErrorCode, ReceiveAudio

router = APIRouter(tags=["audio"])


class AudioAPIError(Exception):
    def __init__(self, status_code: int, error: AudioErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    status_code: int
    error: AudioErrorCode
    message: str


_ERROR_DETAILS = {
    AudioReceptionErrorCode.EMPTY_FILE: _HTTPErrorDetails(
        422,
        "invalid_audio",
        "Arquivo de áudio ausente, vazio ou corrompido.",
    ),
    AudioReceptionErrorCode.FILE_TOO_LARGE: _HTTPErrorDetails(
        413,
        "file_too_large",
        "O arquivo excede o tamanho máximo permitido de 10 MB.",
    ),
    AudioReceptionErrorCode.UNSUPPORTED_FORMAT: _HTTPErrorDetails(
        415,
        "unsupported_format",
        "Formato de áudio não suportado. Formatos aceitos: wav, mp3, m4a, webm.",
    ),
    AudioReceptionErrorCode.CORRUPTED: _HTTPErrorDetails(
        422,
        "invalid_audio",
        "Arquivo de áudio ausente, vazio ou corrompido.",
    ),
    AudioReceptionErrorCode.AUDIO_TOO_LONG: _HTTPErrorDetails(
        422,
        "audio_too_long",
        "O áudio excede a duração máxima permitida de 5 minutos.",
    ),
}


@router.post("/audio", response_model=AudioUploadResponse, status_code=201)
def upload_audio(
    audio: UploadFile = File(...),
    receiver: ReceiveAudio = Depends(get_audio_receiver),
) -> AudioUploadResponse:
    try:
        receipt = receiver.receive(audio.file)
    except AudioReceptionError as exc:
        details = _ERROR_DETAILS[exc.code]
        raise AudioAPIError(details.status_code, details.error, details.message) from exc

    return AudioUploadResponse(
        id=receipt.audio_id,
        status="received",
        message="Áudio recebido com sucesso.",
    )
