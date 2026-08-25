from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, Header, UploadFile

from schemas.audio import AudioErrorCode, AudioUploadResponse
from services.audio_service import MAX_DURATION_SECONDS, AudioProbeError, probe_audio

router = APIRouter(tags=["audio"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class AudioAPIError(Exception):
    def __init__(self, status_code: int, error: AudioErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


def _check_bearer_token(authorization: str | None) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not token:
        raise AudioAPIError(401, "unauthorized", "Token de autenticação ausente ou inválido.")


@router.post("/audio", response_model=AudioUploadResponse, status_code=201)
async def upload_audio(
    audio: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> AudioUploadResponse:
    _check_bearer_token(authorization)

    content = await audio.read()

    if not content:
        raise AudioAPIError(422, "invalid_audio", "Arquivo de áudio ausente, vazio ou corrompido.")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise AudioAPIError(413, "file_too_large", "O arquivo excede o tamanho máximo permitido de 10 MB.")

    probe = probe_audio(content)

    if probe is AudioProbeError.UNSUPPORTED_FORMAT:
        raise AudioAPIError(
            415,
            "unsupported_format",
            "Formato de áudio não suportado. Formatos aceitos: wav, mp3, m4a, webm.",
        )

    if probe is AudioProbeError.CORRUPTED:
        raise AudioAPIError(422, "invalid_audio", "Arquivo de áudio ausente, vazio ou corrompido.")

    if probe.duration_seconds > MAX_DURATION_SECONDS:
        raise AudioAPIError(422, "audio_too_long", "O áudio excede a duração máxima permitida de 5 minutos.")

    return AudioUploadResponse(
        id=f"aud_{uuid4().hex[:12]}",
        status="received",
        message="Áudio recebido com sucesso.",
    )
