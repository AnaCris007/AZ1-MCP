from __future__ import annotations

import os
from dataclasses import dataclass

from google import genai
from google.genai import errors, types

from services.chat_service import ChatModelUnavailableError

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_OUTPUT_TOKENS = 1024

SYSTEM_INSTRUCTION = (
    "Você é o AZ1, assistente conversacional do PMO do Metrô de São Paulo. "
    "Responda em texto corrido, como numa conversa de chat — sem títulos, "
    "tabelas, listas longas ou notação matemática. Seja direto: poucas "
    "frases bastam, a menos que o usuário peça explicitamente mais detalhe."
)


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    model: str

    @classmethod
    def from_environment(cls) -> GeminiSettings:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Gere uma chave gratuita em "
                "https://aistudio.google.com/apikey e defina a variável de ambiente."
            )
        return cls(api_key=api_key, model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))


class GeminiChatModel:
    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: GeminiSettings) -> GeminiChatModel:
        return cls(client=genai.Client(api_key=settings.api_key), model=settings.model)

    def generate_reply(self, message: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                ),
            )
        except errors.ServerError as exc:
            raise ChatModelUnavailableError from exc
        except errors.ClientError as exc:
            if exc.code == 429:
                raise ChatModelUnavailableError from exc
            raise
        return response.text
