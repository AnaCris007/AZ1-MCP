from .analysis import router as analysis_router
from .audio import router as audio_router
from .chat import router as chat_router
from .speech import router as speech_router
from .transcription import router as transcription_router

__all__ = ["analysis_router", "audio_router", "chat_router", "speech_router", "transcription_router"]
