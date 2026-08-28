from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_audio_receiver
from az1_api.main import app
from services.audio_service import (
    AudioReceipt,
    AudioReceptionError,
    AudioReceptionErrorCode,
)


class FakeReceiver:
    def __init__(self, result: AudioReceipt | Exception) -> None:
        self.result = result

    def receive(self, content: object) -> AudioReceipt:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class TestAudioAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: AudioReceipt | Exception) -> TestClient:
        app.dependency_overrides[get_audio_receiver] = lambda: FakeReceiver(result)
        return TestClient(app, raise_server_exceptions=False)

    def test_recebe_audio_sem_header_de_autorizacao(self) -> None:
        client = self._client_with(AudioReceipt(audio_id="aud_123"))

        response = client.post(
            "/api/v1/audio",
            files={"audio": ("consulta.wav", b"audio", "audio/wav")},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "id": "aud_123",
                "status": "received",
                "message": "Áudio recebido com sucesso.",
            },
        )

    def test_retorna_422_quando_campo_audio_esta_ausente(self) -> None:
        client = self._client_with(AudioReceipt(audio_id="nao_utilizado"))

        response = client.post("/api/v1/audio")

        self.assertEqual(response.status_code, 422)

    def test_mapeia_erros_controlados(self) -> None:
        cases = (
            (AudioReceptionErrorCode.EMPTY_FILE, 422, "invalid_audio"),
            (AudioReceptionErrorCode.FILE_TOO_LARGE, 413, "file_too_large"),
            (AudioReceptionErrorCode.UNSUPPORTED_FORMAT, 415, "unsupported_format"),
            (AudioReceptionErrorCode.CORRUPTED, 422, "invalid_audio"),
            (AudioReceptionErrorCode.AUDIO_TOO_LONG, 422, "audio_too_long"),
        )
        for code, status, error in cases:
            with self.subTest(code=code):
                client = self._client_with(AudioReceptionError(code))
                response = client.post(
                    "/api/v1/audio",
                    files={"audio": ("consulta.wav", b"audio", "audio/wav")},
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"], error)

    def test_oculta_detalhes_de_erro_inesperado(self) -> None:
        client = self._client_with(RuntimeError("segredo interno"))

        with self.assertLogs("az1_api.main", level="ERROR"):
            response = client.post(
                "/api/v1/audio",
                files={"audio": ("consulta.wav", b"audio", "audio/wav")},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"error": "internal_error", "message": "Erro interno inesperado."},
        )
        self.assertNotIn("segredo interno", response.text)


if __name__ == "__main__":
    unittest.main()
