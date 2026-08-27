from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from az1_api.dependencies import get_analyzer
from schemas.analysis import AnalysisResponse
from services.analysis_service import AnalyzeAudio
from services.transcription_service import TranscriptionError, TranscriptionErrorCode
from routes.transcription import TranscriptionAPIError

router = APIRouter(tags=["analysis"])

_ERROR_MAP = {
    TranscriptionErrorCode.AUDIO_NOT_FOUND: (404, "audio_not_found", "Áudio não encontrado. O id informado não existe ou já expirou."),
    TranscriptionErrorCode.TRANSCRIPTION_FAILED: (502, "transcription_failed", "Falha ao transcrever o áudio. Tente novamente em instantes."),
}


@router.post("/audio/{audio_id}/analyze", response_model=AnalysisResponse, status_code=200)
async def analyze_audio(
    audio_id: str,
    language: str = Query(default="pt-BR", description="Código BCP-47 do idioma do áudio."),
    analyzer: AnalyzeAudio = Depends(get_analyzer),
) -> AnalysisResponse:
    try:
        result = await analyzer.analyze(audio_id=audio_id, language=language)
    except TranscriptionError as exc:
        status_code, error, message = _ERROR_MAP[exc.code]
        raise TranscriptionAPIError(status_code, error, message) from exc

    return AnalysisResponse(
        audio_id=audio_id,
        text=result.text,
        language=result.language,
        confidence=result.confidence,
        duration_seconds=result.duration_seconds,
        intencao=result.intencao,
        confianca_pln=result.confianca_pln,
    )
