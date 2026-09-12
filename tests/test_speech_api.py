from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_speech_generator, require_authenticated_user
from az1_api.main import app
from services.auth_service import AuthenticatedUser
from services.speech_service import GeneratedSpeech, SpeechGenerationError, SpeechGenerationErrorCode


class FakeSpeechGenerator:
    def __init__(self, result: GeneratedSpeech | Exception) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def generate(self, text: str, voice: str) -> GeneratedSpeech:
        self.calls.append((text, voice))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


_TEST_USER = AuthenticatedUser(subject="test-user", email="teste@example.com", name="Usuário de Teste", provider="azure")


class TestSpeechAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: GeneratedSpeech | Exception) -> tuple[TestClient, FakeSpeechGenerator]:
        generator = FakeSpeechGenerator(result)
        app.dependency_overrides[get_speech_generator] = lambda: generator
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        return TestClient(app, raise_server_exceptions=False), generator

    def test_retorna_audio_wav_com_sucesso(self) -> None:
        client, generator = self._client_with(GeneratedSpeech(content=b"RIFF-audio-WAVE"))

        response = client.post("/api/v1/text-to-speech", json={"text": "Olá"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content, b"RIFF-audio-WAVE")
        self.assertEqual(generator.calls, [("Olá", "Kore")])

    def test_rejeita_voz_ou_formato_nao_suportado(self) -> None:
        client, _ = self._client_with(GeneratedSpeech(content=b"audio"))

        invalid_voice = client.post(
            "/api/v1/text-to-speech", json={"text": "Olá", "voice": "Outra"}
        )
        invalid_format = client.post(
            "/api/v1/text-to-speech", json={"text": "Olá", "format": "mp3"}
        )

        self.assertEqual(invalid_voice.status_code, 422)
        self.assertEqual(invalid_format.status_code, 422)

    def test_mapeia_erros_controlados(self) -> None:
        cases = (
            (SpeechGenerationErrorCode.EMPTY_TEXT, 422, "empty_text"),
            (SpeechGenerationErrorCode.TEXT_TOO_LONG, 422, "text_too_long"),
            (SpeechGenerationErrorCode.PROVIDER_FAILED, 502, "speech_generation_failed"),
        )
        for code, status, error in cases:
            with self.subTest(code=code):
                client, _ = self._client_with(SpeechGenerationError(code))
                response = client.post("/api/v1/text-to-speech", json={"text": "Olá"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"], error)


if __name__ == "__main__":
    unittest.main()

