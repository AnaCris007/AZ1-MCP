from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.transcription_service import (
    TranscribeAudio,
    TranscriptionError,
    TranscriptionErrorCode,
    TranscriptionResult,
)


class FakeFetcher:
    def __init__(self, content: bytes | Exception) -> None:
        self._content = content

    def fetch(self, *, key: str) -> bytes:
        if isinstance(self._content, Exception):
            raise self._content
        return self._content


def _make_deepgram_response(*, transcript: str, confidence: float, duration: float) -> MagicMock:
    alternative = MagicMock()
    alternative.transcript = transcript
    alternative.confidence = confidence

    channel = MagicMock()
    channel.alternatives = [alternative]

    metadata = MagicMock()
    metadata.duration = duration

    response = MagicMock()
    response.results.channels = [channel]
    response.metadata = metadata
    return response


class TestTranscribeAudio(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fetcher = FakeFetcher(b"audio_bytes")
        with patch("services.transcription_service.AsyncDeepgramClient"):
            self.service = TranscribeAudio(fetcher=self.fetcher, api_key="fake-key")

    async def test_retorna_transcricao_com_sucesso(self) -> None:
        fake_response = _make_deepgram_response(
            transcript="Qual o status do projeto?",
            confidence=0.97,
            duration=4.2,
        )
        self.service._client.listen.v1.media.transcribe_file = AsyncMock(return_value=fake_response)

        result = await self.service.transcribe(audio_id="aud_abc123")

        self.assertIsInstance(result, TranscriptionResult)
        self.assertEqual(result.text, "Qual o status do projeto?")
        self.assertAlmostEqual(result.confidence, 0.97)
        self.assertAlmostEqual(result.duration_seconds, 4.2)
        self.assertEqual(result.language, "pt-BR")

    async def test_busca_audio_com_chave_correta(self) -> None:
        fetched_keys: list[str] = []

        class TrackingFetcher:
            def fetch(self, *, key: str) -> bytes:
                fetched_keys.append(key)
                return b"audio"

        fake_response = _make_deepgram_response(transcript="", confidence=0.0, duration=1.0)
        with patch("services.transcription_service.AsyncDeepgramClient"):
            service = TranscribeAudio(fetcher=TrackingFetcher(), api_key="fake-key")
        service._client.listen.v1.media.transcribe_file = AsyncMock(return_value=fake_response)

        await service.transcribe(audio_id="aud_xyz999")

        self.assertEqual(fetched_keys, ["incoming/aud_xyz999"])

    async def test_levanta_audio_not_found_quando_fetcher_falha(self) -> None:
        fetcher = FakeFetcher(KeyError("incoming/aud_xyz"))
        with patch("services.transcription_service.AsyncDeepgramClient"):
            service = TranscribeAudio(fetcher=fetcher, api_key="fake-key")

        with self.assertRaises(TranscriptionError) as ctx:
            await service.transcribe(audio_id="aud_xyz")

        self.assertEqual(ctx.exception.code, TranscriptionErrorCode.AUDIO_NOT_FOUND)

    async def test_levanta_transcription_failed_quando_deepgram_falha(self) -> None:
        self.service._client.listen.v1.media.transcribe_file = AsyncMock(
            side_effect=RuntimeError("timeout")
        )

        with self.assertRaises(TranscriptionError) as ctx:
            await self.service.transcribe(audio_id="aud_abc123")

        self.assertEqual(ctx.exception.code, TranscriptionErrorCode.TRANSCRIPTION_FAILED)

    async def test_repassa_language_para_o_resultado(self) -> None:
        fake_response = _make_deepgram_response(transcript="Hello", confidence=0.9, duration=2.0)
        self.service._client.listen.v1.media.transcribe_file = AsyncMock(return_value=fake_response)

        result = await self.service.transcribe(audio_id="aud_abc123", language="en-US")

        self.assertEqual(result.language, "en-US")


if __name__ == "__main__":
    unittest.main()
