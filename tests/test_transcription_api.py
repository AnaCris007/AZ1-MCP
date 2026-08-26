from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_transcriber
from az1_api.main import app
from services.transcription_service import (
    TranscriptionError,
    TranscriptionErrorCode,
    TranscriptionResult,
)


class FakeTranscriber:
    def __init__(self, result: TranscriptionResult | Exception) -> None:
        self.result = result

    async def transcribe(self, *, audio_id: str, language: str = "pt-BR") -> TranscriptionResult:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class TestTranscriptionAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: TranscriptionResult | Exception) -> TestClient:
        app.dependency_overrides[get_transcriber] = lambda: FakeTranscriber(result)
        return TestClient(app, raise_server_exceptions=False)

    def test_retorna_transcricao_com_sucesso(self) -> None:
        client = self._client_with(
            TranscriptionResult(
                text="Qual o status do projeto Linha 6?",
                language="pt-BR",
                confidence=0.98,
                duration_seconds=3.5,
            )
        )

        response = client.post("/api/v1/audio/aud_abc123/transcribe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "audio_id": "aud_abc123",
                "text": "Qual o status do projeto Linha 6?",
                "language": "pt-BR",
                "confidence": 0.98,
                "duration_seconds": 3.5,
            },
        )

    def test_retorna_404_quando_audio_nao_encontrado(self) -> None:
        client = self._client_with(TranscriptionError(TranscriptionErrorCode.AUDIO_NOT_FOUND))

        response = client.post("/api/v1/audio/aud_inexistente/transcribe")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "audio_not_found")

    def test_retorna_502_quando_deepgram_falha(self) -> None:
        client = self._client_with(TranscriptionError(TranscriptionErrorCode.TRANSCRIPTION_FAILED))

        response = client.post("/api/v1/audio/aud_abc123/transcribe")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "transcription_failed")

    def test_passa_language_como_query_param(self) -> None:
        result = TranscriptionResult(text="Hello", language="en-US", confidence=0.9, duration_seconds=1.0)
        client = self._client_with(result)

        response = client.post("/api/v1/audio/aud_abc123/transcribe?language=en-US")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["language"], "en-US")

    def test_oculta_detalhes_de_erro_inesperado(self) -> None:
        client = self._client_with(RuntimeError("erro interno"))

        with self.assertLogs("az1_api.main", level="ERROR"):
            response = client.post("/api/v1/audio/aud_abc123/transcribe")

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("erro interno", response.text)


if __name__ == "__main__":
    unittest.main()
