import os
from functools import lru_cache

from services.audio_service import ReceiveAudio
from services.storage_service import S3AudioStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio


@lru_cache
def get_audio_receiver() -> ReceiveAudio:
    settings = S3StorageSettings.from_environment()
    return ReceiveAudio(storage=S3AudioStorage.from_settings(settings))


@lru_cache
def get_transcriber() -> TranscribeAudio:
    settings = S3StorageSettings.from_environment()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    return TranscribeAudio(
        fetcher=S3AudioStorage.from_settings(settings),
        api_key=api_key,
    )
