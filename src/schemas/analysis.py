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
    # A previsão crua acima, e a decisão aqui. `intencao` continua sendo o que
    # o modelo achou; `rejeitada` diz se a confiança ficou abaixo do limiar
    # calibrado e, portanto, se o sistema agiria sobre ela.
    rejeitada: bool
