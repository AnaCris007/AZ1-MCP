# Transcreve o áudio e classifica a intenção da fala.
#
# Até aqui este caminho aplicava o modelo CRU: chamava `prever_intencao` e
# devolvia o argmax, sem limiar nenhum. O chat, no mesmo sistema, descartava
# ações abaixo de 0,70. Duas entradas para o mesmo pipeline com regras
# diferentes é a definição de fronteira mal desenhada — agora as duas passam
# por `DetectarIntencao`.

from __future__ import annotations

from dataclasses import dataclass

from pln.intencao import DetectarIntencao, IntencaoDetectada
from services.transcription_service import TranscribeAudio, TranscriptionResult


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    language: str
    confidence: float | None
    duration_seconds: float
    deteccao: IntencaoDetectada

    # `intencao` e `confianca_pln` continuam sendo a previsão CRUA, e não o que
    # sobra da rejeição. O contrato HTTP sempre os descreveu como observação do
    # modelo, e é dela que depende recalibrar o limiar sobre tráfego real
    # depois; quem quer a decisão lê `rejeitada`.
    @property
    def intencao(self) -> str:
        return self.deteccao.prevista

    @property
    def confianca_pln(self) -> float:
        return self.deteccao.confianca

    @property
    def rejeitada(self) -> bool:
        return self.deteccao.rejeitada


class AnalyzeAudio:
    def __init__(self, *, transcriber: TranscribeAudio, detector: DetectarIntencao) -> None:
        self._transcriber = transcriber
        self._detector = detector

    async def analyze(self, *, audio_id: str, language: str = "pt-BR") -> AnalysisResult:
        result: TranscriptionResult = await self._transcriber.transcribe(
            audio_id=audio_id, language=language
        )
        return AnalysisResult(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            duration_seconds=result.duration_seconds,
            deteccao=self._detector(result.text),
        )
