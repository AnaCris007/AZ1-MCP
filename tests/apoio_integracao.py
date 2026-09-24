"""Apoio comum às suítes de integração da Seção 6.4.

Não há caso de teste aqui. O que mora neste módulo são as três coisas que as
suítes TI-01 em diante precisam compartilhar, e que duplicadas apodreceriam em
silêncio:

1. **A massa sintética das fitas.** Esta é a fonte única. Quem gravou
   (`scripts/gravar_fitas_vhs.py`) e quem reproduz (as suítes de transcrição,
   síntese, análise e chat) leem a frase, a voz, o idioma e os termos daqui.
   Escrever a mesma frase nos dois lados faria a chave da fita mudar de um lado
   só — e o replay passaria a procurar uma gravação que ninguém fez, com um
   `RegistroAusente` cuja causa real seria um acento trocado.

2. **O cliente HTTP com a autenticação substituída.** Todas as rotas de negócio
   passaram a exigir sessão válida (RNF02, Seção 3.10), o que é posterior ao
   texto do planejamento — ver a nota de execução da Seção 6.4.5. Nenhum caso de
   integração de OUTRA fronteira deve falhar por 401, então o usuário autenticado
   é injetado por `app.dependency_overrides`. Quem testa a autenticação em si é
   TI-64, e lá o override não é usado.

3. **O áudio de referência.** Os casos de transcrição precisam do mesmo WAV que
   foi enviado ao provedor na gravação, porque é o hash dele que compõe a chave
   da fita de STT. Em vez de versionar o binário, ele é reproduzido da fita de
   TTS — a mesma que TI-11 usa.

A raiz de gravações e o modo são sempre `reproduzir`: nenhuma suíte grava fita.
Gravar é sessão controlada, com credencial e teto de chamadas, e tem roteiro
próprio em `scripts/gravar_fitas_vhs.py`.
"""

from __future__ import annotations

import io
import os
import wave
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from services.auth_service import AuthenticatedUser
from tests.vhs import ChaveVhs, Modo, Vhs, chave_chat, chave_embedding, chave_stt, chave_tts

RAIZ = Path(__file__).resolve().parent.parent
FITAS = RAIZ / "tests" / "fixtures" / "vhs"

# ---------------------------------------------------------------------------
# Massa sintética
# ---------------------------------------------------------------------------
# Inventada, do domínio do AZ1, sem nada do parceiro. Mudar qualquer valor aqui
# muda a chave da fita correspondente (TI-52): o replay passa a exigir uma
# gravação nova, e é assim que deve ser.

FRASE = "Qual é a aderência do projeto de expansão da linha quatro ao portfólio?"
PERGUNTA_CHAT = "Em uma frase, o que é aderência de um projeto ao portfólio?"
TEXTO_EMBEDDING = "relatório de aderência do portfólio de projetos"

VOZ = "Kore"
MODELO_STT = "nova-3"
MODELO_TTS = "gemini-2.5-flash-preview-tts"
MODELO_EMBEDDING = "gemini-embedding-001"
DIMENSAO_EMBEDDING = 1536
IDIOMA = "pt-BR"
TERMOS = ("portfólio", "aderência", "PMO")

SAMPLE_RATE_HZ = 24_000
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1


def silencio(segundos: float = 2.0) -> bytes:
    """WAV de silêncio — a massa do caso de áudio sem fala reconhecível."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as saida:
        saida.setnchannels(CHANNELS)
        saida.setsampwidth(SAMPLE_WIDTH_BYTES)
        saida.setframerate(SAMPLE_RATE_HZ)
        saida.writeframes(b"\x00" * int(SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES * segundos))
    return buffer.getvalue()


class FetcherDeMemoria:
    """Entrega o áudio da massa sem tocar no armazenamento de objetos.

    Implementa o `AudioFetcher` de `services/transcription_service.py`. Usá-lo
    é o que permite às suítes de STT exercitar a fronteira com o provedor sem
    arrastar junto a fronteira com o MinIO, que tem casos próprios (TI-01 a
    TI-05).
    """

    def __init__(self, conteudo: bytes) -> None:
        self._conteudo = conteudo
        self.chaves_pedidas: list[str] = []

    def fetch(self, *, key: str) -> bytes:
        self.chaves_pedidas.append(key)
        return self._conteudo


class FetcherAusente:
    """Fetcher que não acha nada — a causa de `404 audio_not_found`."""

    def fetch(self, *, key: str) -> bytes:
        raise KeyError(key)


# ---------------------------------------------------------------------------
# Módulo VHS
# ---------------------------------------------------------------------------


def leitor_vhs(*, bloquear_rede: bool = True) -> Vhs:
    """O módulo VHS em modo `reproduzir`, com a rede bloqueada.

    Bloquear é o que transforma a promessa de "não sai para a rede" em asserção:
    qualquer tentativa de conexão levanta `RedeBloqueada` em vez de alcançar o
    provedor e fazer o caso passar por acidente.
    """
    return Vhs(raiz=FITAS, modo=Modo.REPRODUZIR, bloquear_rede=bloquear_rede)


def chave_stt_da_massa(audio: bytes, *, cenario: str) -> ChaveVhs:
    return chave_stt(
        audio=audio, idioma=IDIOMA, modelo=MODELO_STT, termos=TERMOS, cenario=cenario
    )


def chave_tts_da_massa(*, texto: str = FRASE, cenario: str = "sucesso") -> ChaveVhs:
    return chave_tts(texto=texto, voz=VOZ, modelo=MODELO_TTS, formato="wav", cenario=cenario)


def chave_chat_da_massa(*, mensagem: str = PERGUNTA_CHAT, cenario: str = "sucesso") -> ChaveVhs:
    """Chave da fita de chat, com a instrução de sistema REAL do agente.

    A instrução entra por import, e não como rótulo: é ela que TI-52 exige na
    chave. Com um texto de fachada, mudar a instrução do agente deixaria a
    chave intacta e o replay serviria a resposta antiga.
    """
    from services.gemini_service import SYSTEM_INSTRUCTION

    return chave_chat(
        mensagem=mensagem,
        instrucao=SYSTEM_INSTRUCTION,
        modelo=modelo_de_chat(),
        cenario=cenario,
    )


def modelo_de_chat() -> str:
    """O modelo que `GeminiSettings.from_environment` escolheria.

    Lido do ambiente, e não fixado, porque é ele que compõe a chave da fita:
    escrever um alias aqui faria o teste procurar a gravação de um modelo que
    não foi o chamado.
    """
    import os

    from services.gemini_service import DEFAULT_MODEL

    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def chave_embedding_da_massa(*, texto: str = TEXTO_EMBEDDING) -> ChaveVhs:
    return chave_embedding(
        texto=texto, modelo=MODELO_EMBEDDING, dimensao=DIMENSAO_EMBEDDING, cenario="sucesso"
    )


@lru_cache(maxsize=1)
def audio_de_referencia() -> bytes:
    """O WAV com fala em português que as fitas de STT tomaram como entrada.

    Reproduzido da fita de TTS em vez de versionado como binário: é o mesmo
    áudio, vem do mesmo lugar de onde veio na gravação, e não acrescenta 220 KB
    ao histórico do Git. O `lru_cache` existe porque abrir a fita a cada caso
    custaria a leitura do YAML inteiro várias vezes por suíte.
    """
    from services.gemini_speech_service import GeminiSpeechModel
    from services.speech_service import GenerateSpeech

    vhs = leitor_vhs()
    with vhs.fita(chave_tts_da_massa()):
        fala = GenerateSpeech(
            GeminiSpeechModel.from_api_key("irrelevante-no-replay", MODELO_TTS)
        ).generate(FRASE, voice=VOZ)
    return fala.content


@contextmanager
def embedding_sem_cache() -> Iterator[None]:
    """Zera os caches do `rag.embedder` e garante uma credencial de fachada.

    Duas coisas atrapalham o replay do embedding, e as duas são `lru_cache`:
    `_cliente` guarda o `genai.Client` e `_consulta_cacheada` guarda o vetor por
    texto. Sem limpar, a segunda chamada devolveria o vetor da memória, a fita
    não seria tocada e o `play_count` ficaria em zero — o caso passaria sem ter
    reproduzido nada.

    A credencial de fachada existe porque `_cliente` recusa subir sem
    `GEMINI_API_KEY`, mesmo quando nada vai à rede. Ela não chega ao provedor:
    a requisição é servida pela fita, e o cabeçalho é sanitizado na gravação.
    """
    from rag import embedder

    anterior = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = anterior or "irrelevante-no-replay"
    embedder._cliente.cache_clear()  # noqa: SLF001 - o cache é o ponto
    embedder.limpar_cache_de_consultas()
    try:
        yield
    finally:
        embedder._cliente.cache_clear()  # noqa: SLF001
        embedder.limpar_cache_de_consultas()
        if anterior is None:
            os.environ.pop("GEMINI_API_KEY", None)


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------

USUARIO_DE_TESTE = AuthenticatedUser(
    subject="ti-integracao",
    email="integracao@example.com",
    name="Usuário das suítes de integração",
    provider="azure",
)


# A aplicação é importada DENTRO das funções, e não no topo do módulo, para que
# `scripts/gravar_fitas_vhs.py` possa importar a massa daqui sem construir a
# FastAPI inteira. A sessão de gravação fala com os adaptadores diretamente; ela
# não precisa de roteador, e arrastar o `app` junto faria o roteiro depender de
# tudo o que `main.py` importa.


def cliente(overrides: Mapping[object, object] | None = None):
    """`TestClient` com a autenticação substituída e as exceções capturadas.

    `raise_server_exceptions=False` é o que o protocolo reproduzível da Seção
    6.4.4 exige para poder observar um 500: sem ele, a exceção sobe pelo
    `TestClient` e o caso quebra em vez de ver a resposta que o cliente real
    veria.
    """
    from fastapi.testclient import TestClient

    from az1_api.dependencies import require_authenticated_user
    from az1_api.main import app

    app.dependency_overrides[require_authenticated_user] = lambda: USUARIO_DE_TESTE
    for dependencia, fabrica in (overrides or {}).items():
        app.dependency_overrides[dependencia] = fabrica
    return TestClient(app, raise_server_exceptions=False)


def limpar_overrides() -> None:
    """Devolve a aplicação ao estado original. Vai no `tearDown` de toda suíte."""
    from az1_api.main import app

    app.dependency_overrides.clear()
