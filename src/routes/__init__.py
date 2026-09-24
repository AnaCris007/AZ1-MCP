from .alerta import router as alerta_router
from .analysis import router as analysis_router
from .audio import router as audio_router
from .auditoria import router as auditoria_router
from .chat import router as chat_router
from .conversas import router as conversas_router
from .portfolio import router as portfolio_router
from .rag import router as rag_router
from .speech import router as speech_router
from .transcription import router as transcription_router
from .voice import router as voice_router
from .webhooks import router as webhooks_router

__all__ = [
    "alerta_router",
    "analysis_router",
    "audio_router",
    "auditoria_router",
    "chat_router",
    "conversas_router",
    "portfolio_router",
    "rag_router",
    "speech_router",
    "transcription_router",
    "voice_router",
    "webhooks_router",
]
