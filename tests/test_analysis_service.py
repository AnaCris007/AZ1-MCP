from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from pln.intencao import DetectarIntencao
from services.analysis_service import AnalysisResult, AnalyzeAudio
from services.transcription_service import TranscriptionError, TranscriptionErrorCode, TranscriptionResult


def _make_transcriber(*, text: str = "texto", confidence: float | None = 0.9, duration: float = 3.0, language: str = "pt-BR") -> MagicMock:
    transcriber = MagicMock()
    transcriber.transcribe = AsyncMock(
        return_value=TranscriptionResult(
            text=text,
            language=language,
            confidence=confidence,
            duration_seconds=duration,
        )
    )
    return transcriber


def _make_modelo(*, intencao: str = "consultar_status", confianca: float = 0.88) -> MagicMock:
    modelo = MagicMock()
    modelo.predict_proba.return_value = np.array([[confianca]])
    modelo.named_steps = {"classificador": MagicMock(classes_=np.array([intencao]))}
    return modelo


# O detector é o REAL sobre um modelo dublê, e não um dublê de detector: o que
# mudou neste serviço foi justamente passar a aplicar a regra de rejeição, e
# dublar o detector esconderia exatamente isso.
def _make_detector(*, intencao: str = "consultar_status", confianca: float = 0.88) -> DetectarIntencao:
    return DetectarIntencao(_make_modelo(intencao=intencao, confianca=confianca))


class TestAnalyzeAudio(unittest.IsolatedAsyncioTestCase):
    async def test_retorna_resultado_completo(self) -> None:
        transcriber = _make_transcriber(text="Qual o status da Linha 6?", confidence=0.95, duration=4.5)
        detector = _make_detector(intencao="consultar_status", confianca=0.91)
        service = AnalyzeAudio(transcriber=transcriber, detector=detector)

        result = await service.analyze(audio_id="aud_abc")

        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.text, "Qual o status da Linha 6?")
        self.assertEqual(result.intencao, "consultar_status")
        self.assertAlmostEqual(result.confianca_pln, 0.91)
        self.assertAlmostEqual(result.confidence, 0.95)
        self.assertAlmostEqual(result.duration_seconds, 4.5)
        self.assertFalse(result.rejeitada)

    async def test_confianca_abaixo_do_limiar_marca_rejeitada(self) -> None:
        """O caminho de áudio passou a aplicar a MESMA regra do chat.

        Antes ele devolvia o argmax cru, sem limiar nenhum: a mesma frase
        produzia decisões diferentes conforme entrasse por voz ou por texto.

        `intencao` continua sendo a previsão crua de propósito — é observação,
        e é dela que depende recalibrar o limiar sobre tráfego real. Quem quer
        a decisão lê `rejeitada`.
        """
        transcriber = _make_transcriber()
        service = AnalyzeAudio(
            transcriber=transcriber, detector=_make_detector(confianca=0.10)
        )

        result = await service.analyze(audio_id="aud_abc")

        self.assertTrue(result.rejeitada)
        self.assertEqual(result.intencao, "consultar_status")

    async def test_repassa_language_para_transcricao(self) -> None:
        transcriber = _make_transcriber(language="en-US")
        service = AnalyzeAudio(transcriber=transcriber, detector=_make_detector())

        result = await service.analyze(audio_id="aud_abc", language="en-US")

        transcriber.transcribe.assert_awaited_once_with(audio_id="aud_abc", language="en-US")
        self.assertEqual(result.language, "en-US")

    async def test_propaga_transcription_error(self) -> None:
        transcriber = MagicMock()
        transcriber.transcribe = AsyncMock(
            side_effect=TranscriptionError(TranscriptionErrorCode.AUDIO_NOT_FOUND)
        )
        service = AnalyzeAudio(transcriber=transcriber, detector=_make_detector())

        with self.assertRaises(TranscriptionError) as ctx:
            await service.analyze(audio_id="aud_inexistente")

        self.assertEqual(ctx.exception.code, TranscriptionErrorCode.AUDIO_NOT_FOUND)

    async def test_confidence_pode_ser_none(self) -> None:
        transcriber = _make_transcriber(confidence=None)
        service = AnalyzeAudio(transcriber=transcriber, detector=_make_detector())

        result = await service.analyze(audio_id="aud_abc")

        self.assertIsNone(result.confidence)


if __name__ == "__main__":
    unittest.main()
