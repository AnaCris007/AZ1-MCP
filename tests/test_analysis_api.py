from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_analyzer, require_authenticated_user
from az1_api.main import app
from pln.intencao import IntencaoDetectada
from services.analysis_service import AnalysisResult
from services.auth_service import AuthenticatedUser
from services.transcription_service import TranscriptionError, TranscriptionErrorCode


class FakeAnalyzer:
    def __init__(self, result: AnalysisResult | Exception) -> None:
        self.result = result

    async def analyze(self, *, audio_id: str, language: str = "pt-BR") -> AnalysisResult:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


_RESULTADO_PADRAO = AnalysisResult(
    text="Qual o status da Linha 6?",
    language="pt-BR",
    confidence=0.95,
    duration_seconds=4.5,
    deteccao=IntencaoDetectada(prevista="consultar_status", confianca=0.88),
)

_TEST_USER = AuthenticatedUser(subject="test-user", email="teste@example.com", name="Usuário de Teste", provider="azure")


class TestAnalysisAPI(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _client_with(self, result: AnalysisResult | Exception) -> TestClient:
        app.dependency_overrides[get_analyzer] = lambda: FakeAnalyzer(result)
        app.dependency_overrides[require_authenticated_user] = lambda: _TEST_USER
        return TestClient(app, raise_server_exceptions=False)

    def test_retorna_analise_completa(self) -> None:
        client = self._client_with(_RESULTADO_PADRAO)

        response = client.post("/api/v1/audio/aud_abc123/analyze")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "audio_id": "aud_abc123",
                "text": "Qual o status da Linha 6?",
                "language": "pt-BR",
                "confidence": 0.95,
                "duration_seconds": 4.5,
                "intencao": "consultar_status",
                "confianca_pln": 0.88,
                "rejeitada": False,
            },
        )

    def test_retorna_404_quando_audio_nao_encontrado(self) -> None:
        client = self._client_with(TranscriptionError(TranscriptionErrorCode.AUDIO_NOT_FOUND))

        response = client.post("/api/v1/audio/aud_inexistente/analyze")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "audio_not_found")

    def test_retorna_502_quando_transcricao_falha(self) -> None:
        client = self._client_with(TranscriptionError(TranscriptionErrorCode.TRANSCRIPTION_FAILED))

        response = client.post("/api/v1/audio/aud_abc123/analyze")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "transcription_failed")

    def test_rejeita_idioma_nao_suportado(self) -> None:
        result = AnalysisResult(
            text="Hello", language="en-US", confidence=0.9,
            duration_seconds=1.0,
            deteccao=IntencaoDetectada(prevista="fora_do_catalogo", confianca=0.6),
        )
        client = self._client_with(result)

        response = client.post("/api/v1/audio/aud_abc123/analyze?language=en-US")

        self.assertEqual(response.status_code, 422)

    def test_oculta_detalhes_de_erro_inesperado(self) -> None:
        client = self._client_with(RuntimeError("erro interno"))

        with self.assertLogs("az1_api.main", level="ERROR"):
            response = client.post("/api/v1/audio/aud_abc123/analyze")

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("erro interno", response.text)


if __name__ == "__main__":
    unittest.main()
