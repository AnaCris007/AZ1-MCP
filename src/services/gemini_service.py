from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto

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
    "Responda EXCLUSIVAMENTE com base nos trechos numerados abaixo, recuperados "
    "dos documentos do portfólio. Ao final de cada afirmação que dependa de um "
    "trecho, cite o número dele entre colchetes, assim: [1]. Se os trechos não "
    "contiverem a informação pedida, diga isso e pare — não complete com "
    "conhecimento próprio, não estime percentuais, não deduza datas nem valores. "
    "Não invente número de trecho nem cite um que você não usou."
)

# Respostas canônicas: são devolvidas SEM chamar o modelo, de propósito.
#
# A versão anterior instruía o modelo a "responder como se já soubesse a
# informação" e, quando a busca falhava, mandava a pergunta crua para o Gemini.
# O resultado era um agente de PMO produzindo percentuais e datas com a forma
# certa e sem lastro nenhum — e foi o que aconteceu, por semanas, porque a
# coleção vetorial estava com dimensão incompatível e a exceção era engolida.
#
# Determinismo aqui não é preciosismo: é a única forma de garantir que a recusa
# aconteça 100% das vezes. Delegar a recusa ao próprio modelo é pedir que ele
# decida não responder — exatamente o que ele é treinado para evitar.
MENSAGEM_SEM_FUNDAMENTO = (
    "Não encontrei essa informação nos documentos do portfólio que tenho "
    "indexados. Posso ajudar com outra pergunta sobre os projetos, os "
    "cronogramas, os riscos ou os termos de abertura."
)

MENSAGEM_BASE_INDISPONIVEL = (
    "Não consegui consultar a base de documentos agora, então prefiro não "
    "responder a partir de suposição. Tente de novo em instantes."
)

# Similaridade mínima para um trecho ser considerado fundamento.
#
# A busca vetorial sempre devolve os k mais próximos, mesmo para uma pergunta
# fora do assunto — sem um piso, qualquer coisa "tem fonte" e a citação vira
# teatro.
#
# MEDIDO contra a base reindexada (164 chunks, 1536 dimensões), com quatro
# consultas de sondagem:
#
#   dentro do escopo  0,668 – 0,724   ("riscos da ventilação", "avanço do portfólio")
#   fora do escopo    0,504 – 0,569   ("capital da França", "bolo de chocolate")
#
# 0,60 cai na folga entre as duas faixas, com margem dos dois lados. Quatro
# consultas é amostra pequena: se perguntas legítimas começarem a receber a
# mensagem padrão, o valor está alto; se assunto alheio voltar a "ter fonte",
# está baixo. Reavaliar quando a base crescer — a distância entre as faixas
# tende a encolher com mais documentos.
SCORE_MINIMO_CONTEXTO = 0.60


class _Situacao(Enum):
    """Em que pé a recuperação ficou, antes de decidir se chama o modelo."""

    COM_FUNDAMENTO = auto()
    SEM_FUNDAMENTO = auto()
    BASE_INDISPONIVEL = auto()
    SEM_BUSCA = auto()


@dataclass(frozen=True)
class RespostaGerada:
    """O texto e os trechos que o fundamentaram.

    `generate_reply` devolvia só a string, e os `ResultadoBusca` morriam dentro
    de `_com_contexto_recuperado`. Sem eles não há como citar a fonte na
    resposta nem gravar `auditoria.mensagem_fonte` — os dois pilares do RNF12.

    `fontes` vem na MESMA ordem da numeração do prompt, de modo que o `[2]` que
    o modelo cita seja `fontes[1]`. É o que torna a citação verificável em vez
    de decorativa.
    """

    texto: str
    fontes: tuple[ResultadoBusca, ...] = ()


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

    def generate_reply(
        self, message: str, *, conversation_id: str | None = None
    ) -> RespostaGerada:
        historico = self._historico.get(conversation_id, []) if conversation_id else []

        texto_enviado, fontes, situacao = self._preparar(message)

        # As duas situações abaixo devolvem resposta canônica SEM chamar o
        # modelo. Mandar a pergunta crua nesses casos é o que produzia respostas
        # inventadas — ver o comentário em MENSAGEM_SEM_FUNDAMENTO.
        if situacao is _Situacao.SEM_FUNDAMENTO:
            return RespostaGerada(texto=MENSAGEM_SEM_FUNDAMENTO)
        if situacao is _Situacao.BASE_INDISPONIVEL:
            return RespostaGerada(texto=MENSAGEM_BASE_INDISPONIVEL)

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

        return RespostaGerada(texto=reply_text, fontes=fontes)

    def _preparar(self, message: str) -> tuple[str, tuple[ResultadoBusca, ...], _Situacao]:
        """Decide o que enviar ao modelo, e se vale enviar alguma coisa.

        Sem buscador injetado, o comportamento é o de antes: pergunta crua, sem
        contexto. É o caso dos testes e de qualquer instalação sem RAG — recusar
        ali transformaria "sem busca configurada" em "não sei nada".
        """
        if self._buscar_contexto is None:
            return message, (), _Situacao.SEM_BUSCA

        try:
            resultados = list(self._buscar_contexto(message))
        except Exception:
            # Antes isto respondia sem contexto, o que deixava o modelo preencher
            # a lacuna. Indisponibilidade da base agora é dita, não disfarçada.
            logger.exception("Falha ao consultar a base de documentos.")
            return message, (), _Situacao.BASE_INDISPONIVEL

        relevantes = tuple(r for r in resultados if r.score >= SCORE_MINIMO_CONTEXTO)
        if not relevantes:
            logger.info(
                "Sem trecho acima de %.2f para a pergunta; respondendo com a mensagem padrão.",
                SCORE_MINIMO_CONTEXTO,
            )
            return message, (), _Situacao.SEM_FUNDAMENTO

        trechos = "\n\n".join(
            f"[{n}] {r.arquivo_origem}" + (f" — {r.secao}" if r.secao else "") + f"\n{r.texto}"
            for n, r in enumerate(relevantes, start=1)
        )
        prompt = f"{CONTEXTO_INSTRUCAO}\n\n{trechos}\n\nPergunta do usuário: {message}"
        return prompt, relevantes, _Situacao.COM_FUNDAMENTO
