from .analysis import router as analysis_router
from .audio import router as audio_router
from .chat import router as chat_router
from .transcription import router as transcription_router
from .webhooks import router as webhooks_router

__all__ = [
    "analysis_router",
    "audio_router",
    "chat_router",
    "transcription_router",
    "webhooks_router",
]
