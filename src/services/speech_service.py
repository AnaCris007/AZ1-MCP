from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

MAX_SPEECH_TEXT_LENGTH = 4000
SAMPLE_RATE_HZ = 24_000
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1


class SpeechModel(Protocol):
    def generate_pcm(self, text: str, voice: str) -> bytes: ...


class SpeechGenerationErrorCode(Enum):
    EMPTY_TEXT = auto()
    TEXT_TOO_LONG = auto()
    PROVIDER_FAILED = auto()


class SpeechGenerationError(Exception):
    def __init__(self, code: SpeechGenerationErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class GeneratedSpeech:
    content: bytes
    media_type: str = "audio/wav"
    filename: str = "speech.wav"


def pcm_to_wav(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(SAMPLE_RATE_HZ)
        wav_file.writeframes(pcm)
    return output.getvalue()


class GenerateSpeech:
    def __init__(self, model: SpeechModel) -> None:
        self._model = model

    def generate(self, text: str, voice: str = "Kore") -> GeneratedSpeech:
        trimmed = text.strip()
        if not trimmed:
            raise SpeechGenerationError(SpeechGenerationErrorCode.EMPTY_TEXT)
        if len(trimmed) > MAX_SPEECH_TEXT_LENGTH:
            raise SpeechGenerationError(SpeechGenerationErrorCode.TEXT_TOO_LONG)

        try:
            pcm = self._model.generate_pcm(trimmed, voice)
        except SpeechGenerationError:
            raise
        except Exception as exc:
            raise SpeechGenerationError(SpeechGenerationErrorCode.PROVIDER_FAILED) from exc

        if not pcm:
            raise SpeechGenerationError(SpeechGenerationErrorCode.PROVIDER_FAILED)
        return GeneratedSpeech(content=pcm_to_wav(pcm))

