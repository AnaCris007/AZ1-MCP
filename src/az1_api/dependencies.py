from functools import lru_cache

from services.audio_service import ReceiveAudio
from services.chat_service import AnswerChatMessage
from services.gemini_service import GeminiChatModel, GeminiSettings
from services.storage_service import S3AudioStorage, S3StorageSettings


@lru_cache
def get_audio_receiver() -> ReceiveAudio:
    settings = S3StorageSettings.from_environment()
    return ReceiveAudio(storage=S3AudioStorage.from_settings(settings))


@lru_cache
def get_chat_answerer() -> AnswerChatMessage:
    settings = GeminiSettings.from_environment()
    return AnswerChatMessage(model=GeminiChatModel.from_settings(settings))
