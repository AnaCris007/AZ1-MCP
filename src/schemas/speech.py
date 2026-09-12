from typing import Literal

from pydantic import BaseModel

SpeechVoice = Literal["Kore"]
SpeechAudioFormat = Literal["wav"]
SpeechErrorCode = Literal["empty_text", "text_too_long", "speech_generation_failed"]


class SpeechRequest(BaseModel):
    text: str
    voice: SpeechVoice = "Kore"
    format: SpeechAudioFormat = "wav"

