from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from google import genai
from google.genai import errors, types

from rag.retriever import ResultadoBusca
from services.chat_service import ChatModelUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_OUTPUT_TOKENS = 1024

SYSTEM_INSTRUCTION = (
    "Você é o AZ1, assistente conversacional do PMO do Metrô de São Paulo. "
    "Responda em texto corrido, como numa conversa de chat — sem títulos, "
    "tabelas, listas longas ou notação matemática. Seja direto: poucas "
    "frases bastam, a menos que o usuário peça explicitamente mais detalhe. "
    "Nunca comece respostas com saudações como 'Olá!' — vá direto ao ponto."
)

CONTEXTO_INSTRUCAO = (
    "Use os trechos abaixo, recuperados da base de conhecimento do projeto, "
    "como referência se forem relevantes para a pergunta. Não mencione a "
    "existência desses trechos; responda como se já soubesse a informação."
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
    def __init__(
        self,
        client: genai.Client,
        model: str,
        *,
        buscar_contexto: Callable[[str], Sequence[ResultadoBusca]] | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._historico: dict[str, list] = {}
        self._buscar_contexto = buscar_contexto

    @classmethod
    def from_settings(
        cls,
        settings: GeminiSettings,
        *,
        buscar_contexto: Callable[[str], Sequence[ResultadoBusca]] | None = None,
    ) -> GeminiChatModel:
        return cls(
            client=genai.Client(api_key=settings.api_key),
            model=settings.model,
            buscar_contexto=buscar_contexto,
        )

    def generate_reply(self, message: str, *, conversation_id: str | None = None) -> str:
        historico = self._historico.get(conversation_id, []) if conversation_id else []
        texto_enviado = self._com_contexto_recuperado(message)
        contents = historico + [{"role": "user", "parts": [{"text": texto_enviado}]}]

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
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

        reply_text = response.text

        if conversation_id:
            self._historico[conversation_id] = historico + [
                {"role": "user", "parts": [{"text": message}]},
                {"role": "model", "parts": [{"text": reply_text}]},
            ]

        return reply_text

    def _com_contexto_recuperado(self, message: str) -> str:
        if self._buscar_contexto is None:
            return message

        try:
            resultados = self._buscar_contexto(message)
        except Exception:
            logger.exception("Falha ao consultar o RAG; respondendo sem contexto recuperado.")
            return message

        if not resultados:
            return message

        trechos = "\n\n".join(
            f"Fonte: {r.arquivo_origem} ({r.secao})\n{r.texto}" for r in resultados
        )
        return f"{CONTEXTO_INSTRUCAO}\n\n{trechos}\n\nPergunta do usuário: {message}"
