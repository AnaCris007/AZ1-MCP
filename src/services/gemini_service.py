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
    "Não invente número de trecho nem cite um que você não usou.\n\n"
    "ATENÇÃO AO PROJETO: cada trecho começa indicando a que projeto pertence. "
    "A busca traz trechos de projetos diferentes, e todos os projetos têm "
    "documentos com o mesmo nome. Nunca atribua a um projeto uma informação "
    "que veio do trecho de outro. Se a pergunta é sobre um projeto específico, "
    "use apenas os trechos daquele projeto; se algum trecho relevante for de "
    "outro, diga de qual é em vez de misturar."
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
# MEDIDO contra a base reindexada (164 chunks, 1536 dimensões). São TRÊS faixas,
# e não duas — foi a terceira que surpreendeu:
#
#   assunto alheio      0,504 – 0,569   ("capital da França", "bolo de chocolate")
#   saudação / meta     0,607 – 0,666   ("oi", "bom dia", "obrigado")
#   dentro do escopo    0,668 – 0,724   ("riscos da ventilação", "avanço do portfólio")
#
# 0,60 separa a PRIMEIRA faixa das outras duas. Saudação passa de propósito: ela
# chega ao modelo com contexto, e quem a trata bem é a instrução ("se os trechos
# não contiverem a informação, diga isso") — que a devolve como um convite a
# perguntar, em vez da recusa seca da mensagem padrão. Como o modelo não cita
# nada nesse caso, nenhuma fonte é exibida.
#
# ESPAÇO DE MANOBRA É MÍNIMO PARA CIMA: a distância entre saudação (0,666) e
# pergunta legítima (0,668) é de 0,002. Subir o limiar para barrar assunto
# alheio com mais folga barra as saudações primeiro e, logo em seguida, começa a
# recusar pergunta boa. Para cima, praticamente não há espaço; para baixo, há.
#
# A amostra ainda é pequena. Reavaliar quando a base crescer: mais documentos
# aproximam as faixas, e a separação tende a piorar, não melhorar.
SCORE_MINIMO_CONTEXTO = 0.60


def _formatar_trecho(numero: int, resultado: ResultadoBusca) -> str:
    """Cabeçalho do trecho no prompt.

    O `projeto_id` é obrigatório aqui, e a razão é concreta: cada projeto tem um
    arquivo chamado `04_Riscos_e_Problemas.xlsx`. Sem o código do projeto no
    cabeçalho, o modelo não tem como distinguir os riscos do SYN-01 dos do
    SYN-02 — e, perguntado sobre um, respondeu misturando os dois, atribuindo à
    ventilação três riscos que eram de outro projeto.

    O nome do arquivo sozinho identifica o TIPO de documento, nunca a que
    projeto ele pertence.
    """
    partes = [f"[{numero}] Projeto {resultado.projeto_id}"]
    if resultado.tipo_documento and resultado.tipo_documento != "desconhecido":
        partes.append(resultado.tipo_documento.replace("_", " "))
    partes.append(resultado.arquivo_origem)
    if resultado.secao:
        partes.append(resultado.secao)
    return " — ".join(partes) + f"\n{resultado.texto}"


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

    # `auditoria.mensagem.resultado` tem CHECK ('sucesso','esclarecimento',
    # 'recusada','falha'). Quem sabe qual foi o desfecho é este módulo, não a
    # rota: a recusa por falta de fundamento acontece aqui dentro. Gravado como
    # 'sucesso' literal, como era antes, o relatório de auditoria não consegue
    # distinguir uma resposta fundamentada de uma recusa.
    resultado: str = "sucesso"
    modelo: str = ""


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
        carregar_historico: Callable[[str], Sequence[tuple[str, str]]] | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._buscar_contexto = buscar_contexto
        self._carregar_historico = carregar_historico
        # Só usado quando não há `carregar_historico`. Um `dict` de processo que
        # nunca expira é vazamento de memória e, com mais de um worker, devolve
        # históricos diferentes conforme quem atende. Com o banco gravando a
        # trilha, ele deixou de ser a fonte — virou o modo degradado.
        self._historico_em_memoria: dict[str, list] = {}

    @classmethod
    def from_settings(
        cls,
        settings: GeminiSettings,
        *,
        buscar_contexto: Callable[[str], Sequence[ResultadoBusca]] | None = None,
        carregar_historico: Callable[[str], Sequence[tuple[str, str]]] | None = None,
    ) -> GeminiChatModel:
        return cls(
            client=genai.Client(api_key=settings.api_key),
            model=settings.model,
            buscar_contexto=buscar_contexto,
            carregar_historico=carregar_historico,
        )

    def generate_reply(
        self, message: str, *, conversation_id: str | None = None
    ) -> RespostaGerada:
        historico = self._historico_de(conversation_id)

        texto_enviado, fontes, situacao = self._preparar(message)

        # As duas situações abaixo devolvem resposta canônica SEM chamar o
        # modelo. Mandar a pergunta crua nesses casos é o que produzia respostas
        # inventadas — ver o comentário em MENSAGEM_SEM_FUNDAMENTO.
        if situacao is _Situacao.SEM_FUNDAMENTO:
            return RespostaGerada(texto=MENSAGEM_SEM_FUNDAMENTO, resultado="recusada")
        if situacao is _Situacao.BASE_INDISPONIVEL:
            return RespostaGerada(texto=MENSAGEM_BASE_INDISPONIVEL, resultado="falha")

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

        # Só alimenta o cache de memória quando ele É a fonte. Com o histórico
        # vindo do banco, guardar aqui seria manter duas verdades.
        if conversation_id and self._carregar_historico is None:
            self._historico_em_memoria[conversation_id] = historico + [
                {"role": "user", "parts": [{"text": message}]},
                {"role": "model", "parts": [{"text": reply_text}]},
            ]

        return RespostaGerada(texto=reply_text, fontes=fontes, modelo=self._model)

    def _historico_de(self, conversation_id: str | None) -> list:
        """Os turnos anteriores da conversa, do banco quando possível.

        A trilha em `auditoria.mensagem` é a fonte: sobrevive a recarregar a
        página, a reiniciar o processo e a mais de um worker — nenhuma das três
        coisas o `dict` de memória fazia.

        Falha de leitura degrada para "sem histórico" em vez de derrubar a
        conversa: perder o contexto de turnos anteriores é ruim, não responder é
        pior.
        """
        if not conversation_id:
            return []

        if self._carregar_historico is None:
            return self._historico_em_memoria.get(conversation_id, [])

        try:
            turnos = self._carregar_historico(conversation_id)
        except Exception:
            logger.exception("Falha ao carregar o histórico; seguindo sem ele.")
            return []

        return [
            {"role": "user" if papel == "usuario" else "model", "parts": [{"text": texto}]}
            for papel, texto in turnos
        ]

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

        trechos = "\n\n".join(_formatar_trecho(n, r) for n, r in enumerate(relevantes, start=1))
        prompt = f"{CONTEXTO_INSTRUCAO}\n\n{trechos}\n\nPergunta do usuário: {message}"
        return prompt, relevantes, _Situacao.COM_FUNDAMENTO
