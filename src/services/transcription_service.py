from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from deepgram import AsyncDeepgramClient

_DOMAIN_KEYTERMS = [
    "PMO",
    "Metrô de São Paulo",
    "empreendimento",
    "cronograma",
    "marco",
    "risco",
    "portfólio",
    "programa",
    "contrato",
    "obra",
    "pendência",
    "avanço físico",
]

_DEEPGRAM_MODEL = "nova-3"


class AudioFetcher(Protocol):
    def fetch(self, *, key: str) -> bytes: ...


class TranscriptionErrorCode(Enum):
    AUDIO_NOT_FOUND = auto()
    TRANSCRIPTION_FAILED = auto()


class TranscriptionError(Exception):
    def __init__(self, code: TranscriptionErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    confidence: float | None
    duration_seconds: float


class TranscribeAudio:
    def __init__(self, fetcher: AudioFetcher, api_key: str) -> None:
        self._fetcher = fetcher
        self._client = AsyncDeepgramClient(api_key=api_key)

    async def transcribe(self, *, audio_id: str, language: str = "pt-BR") -> TranscriptionResult:
        try:
            content = self._fetcher.fetch(key=f"incoming/{audio_id}")
        except KeyError as exc:
            raise TranscriptionError(TranscriptionErrorCode.AUDIO_NOT_FOUND) from exc

        return await self.transcribe_content(content=content, language=language)

    async def transcribe_content(
        self, *, content: bytes, language: str = "pt-BR"
    ) -> TranscriptionResult:
        try:
            response = await self._client.listen.v1.media.transcribe_file(
                request=content,
                model=_DEEPGRAM_MODEL,
                language=language,
                smart_format=True,
                punctuate=True,
                keyterm=_DOMAIN_KEYTERMS,
            )
        except Exception as exc:
            raise TranscriptionError(TranscriptionErrorCode.TRANSCRIPTION_FAILED) from exc

        best = response.results.channels[0].alternatives[0]
        return TranscriptionResult(
            text=best.transcript or "",
            language=language,
            confidence=best.confidence,
            duration_seconds=response.metadata.duration,
        )
