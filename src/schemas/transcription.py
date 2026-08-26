from typing import Literal

from pydantic import BaseModel

TranscriptionErrorCode = Literal[
    "audio_not_found",
    "transcription_failed",
]


class TranscriptionResponse(BaseModel):
    audio_id: str
    text: str
    language: str
    confidence: float | None
    duration_seconds: float
