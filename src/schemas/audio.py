from typing import Literal

from pydantic import BaseModel

AudioStatus = Literal["received"]

AudioErrorCode = Literal[
    "bad_request",
    "unsupported_format",
    "file_too_large",
    "audio_too_long",
    "invalid_audio",
    "internal_error",
]


class AudioUploadResponse(BaseModel):
    id: str
    status: AudioStatus
    message: str


class ErrorResponse(BaseModel):
    error: AudioErrorCode
    message: str
