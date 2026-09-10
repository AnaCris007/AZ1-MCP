from __future__ import annotations

from google import genai
from google.genai import types

DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"


class GeminiSpeechModel:
    def __init__(self, client: genai.Client, model: str = DEFAULT_TTS_MODEL) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_api_key(cls, api_key: str, model: str = DEFAULT_TTS_MODEL) -> GeminiSpeechModel:
        return cls(client=genai.Client(api_key=api_key), model=model)

    def generate_pcm(self, text: str, voice: str) -> bytes:
        response = self._client.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        parts = response.candidates[0].content.parts
        audio = parts[0].inline_data.data if parts and parts[0].inline_data else None
        if not audio:
            raise RuntimeError("O Gemini não retornou conteúdo de áudio.")
        return audio

