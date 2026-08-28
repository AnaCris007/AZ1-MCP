from __future__ import annotations

from dataclasses import dataclass

from sklearn.pipeline import Pipeline

from pln.classificador import prever_intencao
from services.transcription_service import TranscribeAudio, TranscriptionResult


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    language: str
    confidence: float | None
    duration_seconds: float
    intencao: str
    confianca_pln: float


class AnalyzeAudio:
    def __init__(self, *, transcriber: TranscribeAudio, modelo: Pipeline) -> None:
        self._transcriber = transcriber
        self._modelo = modelo

    async def analyze(self, *, audio_id: str, language: str = "pt-BR") -> AnalysisResult:
        result: TranscriptionResult = await self._transcriber.transcribe(
            audio_id=audio_id, language=language
        )
        intencao, confianca_pln = prever_intencao(self._modelo, result.text)
        return AnalysisResult(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            duration_seconds=result.duration_seconds,
            intencao=intencao,
            confianca_pln=confianca_pln,
        )
