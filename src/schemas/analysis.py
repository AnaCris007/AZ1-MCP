from __future__ import annotations

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    audio_id: str
    text: str
    language: str
    confidence: float | None
    duration_seconds: float
    intencao: str
    confianca_pln: float
