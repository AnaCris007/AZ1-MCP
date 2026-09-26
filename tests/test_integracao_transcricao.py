"""Transcrição e provedor de fala em texto — casos TI-06 a TI-10 (Seção 6.4.4).

A fronteira sob teste é a que separa `TranscribeAudio` do Deepgram. Ela é
atravessada de verdade: o adaptador é o de produção, o SDK é o `deepgram-sdk`
instalado, e o transporte `httpx` por baixo dele é interceptado pelo módulo VHS,
que serve uma resposta REAL gravada em sessão controlada (Seção 6.4.3). A rede
fica bloqueada durante todo o replay, de modo que um caso que passasse por ter
alcançado o provedor falharia com `RedeBloqueada` em vez de passar.

O que cada mecanismo cobre, e por quê:

- **TI-06 e TI-08** leem fita de sucesso. São respostas genuínas do provedor —
  uma com fala, outra com silêncio —, e o que elas provam é o contrato de
  desserialização: que `response.results.channels[0].alternatives[0]` continua
  existindo e que os campos chegam ao schema Pydantic com os tipos certos.
- **TI-07** combina as duas origens que a Seção 6.4.2 distingue. A credencial
  inválida foi gravada de verdade, porque há resposta HTTP para capturar: o
  provedor recusa com 401. Indisponibilidade e tempo limite NÃO têm resposta
  HTTP — não há o que gravar —, e por isso são simuladas no transporte, com a
  origem identificada no nome de cada variante.
- **TI-09** não chega ao provedor: o `Literal["pt-BR"]` do schema recusa antes.
  O contador do dublê é o que transforma "não deve chamar" em asserção.
- **TI-10** é a exceção que não passa pelo VHS, e a Seção 6.4.4 explica por quê:
  em replay o cliente real nunca é acionado, então nada garantiria que o código
  de produção continua enviando `keyterm`. Aqui o cliente é um espião.

Execução:

    python -m unittest tests.test_integracao_transcricao -v

Não requer credencial, rede nem contêiner: tudo vem das fitas versionadas.
"""

from __future__ import annotations

import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import httpx

from az1_api.dependencies import get_transcriber
from services.transcription_service import (
    _DEEPGRAM_MODEL,
    _DOMAIN_KEYTERMS,
    TranscribeAudio,
)
from tests.apoio_integracao import (
    IDIOMA,
    FetcherDeMemoria,
    audio_de_referencia,
    chave_stt_da_massa,
    cliente,
    leitor_vhs,
    limpar_overrides,
    silencio,
)

CHAVE_IRRELEVANTE = "irrelevante-no-replay"


class _ClienteEspiao:
    """Substitui o `AsyncDeepgramClient` e guarda os argumentos da chamada.

    A forma imita a do SDK — `cliente.listen.v1.media.transcribe_file(...)` — e
    não é acidente: é justamente essa cadeia de atributos que TI-10 precisa ver
    o código de produção percorrer.
    """

    def __init__(self, resposta: object | None = None) -> None:
        self.chamadas: list[dict] = []
        self._resposta = resposta
        self.listen = self
        self.v1 = self
        self.media = self

    async def transcribe_file(self, **argumentos: object) -> object:
        self.chamadas.append(argumentos)
        if self._resposta is None:
            raise AssertionError("o provedor não deveria ter sido acionado")
        return self._resposta


def _resposta_deepgram_minima(
    *, texto: str = "texto de referência", confianca: float = 0.97, duracao: float = 3.5
) -> SimpleNamespace:
    """O mínimo da resposta do SDK que `TranscribeAudio` lê.

    Só existe para o caso do espião: TI-10 verifica o que SAI para o provedor,
    e precisa de algo plausível de volta para que a rota chegue ao fim.
    """
    alternativa = SimpleNamespace(transcript=texto, confidence=confianca)
    return SimpleNamespace(
        results=SimpleNamespace(channels=[SimpleNamespace(alternatives=[alternativa])]),
        metadata=SimpleNamespace(duration=duracao),
    )


def _transcritor_de(audio: bytes) -> TranscribeAudio:
    """O adaptador de produção, com o armazenamento trocado por memória.

    Trocar o fetcher isola a fronteira: quem está sob teste aqui é o provedor de
    transcrição, e a fronteira com o MinIO tem casos próprios (TI-01 a TI-05).
    """
    return TranscribeAudio(FetcherDeMemoria(audio), CHAVE_IRRELEVANTE)


def _clientes_httpx(raiz: object, profundidade: int = 4) -> list[httpx.AsyncClient]:
    """Varre o objeto do SDK atrás dos `httpx.AsyncClient` que ele mantém.

    Necessário porque o caminho até o transporte muda entre versões do
    `deepgram-sdk`, e fixá-lo faria o caso quebrar num upgrade por um motivo que
    não é o que ele testa.
    """
    encontrados: list[httpx.AsyncClient] = []
    identidades: set[int] = set()
    pilha: list[tuple[object, int]] = [(raiz, 0)]
    while pilha:
        objeto, nivel = pilha.pop()
        if nivel > profundidade or id(objeto) in identidades:
            continue
        identidades.add(id(objeto))
        if isinstance(objeto, httpx.AsyncClient):
            encontrados.append(objeto)
            continue
        for nome in getattr(objeto, "__dict__", {}):
            pilha.append((getattr(objeto, nome, None), nivel + 1))
    return encontrados


@contextmanager
def _transporte_que_levanta(transcritor: TranscribeAudio, erro: Exception) -> Iterator[None]:
    """Injeta a falha ABAIXO do SDK, no transporte, e não no adaptador.

    Levantar direto de um dublê de `TranscribeAudio` provaria apenas que o
    `except` existe. Injetando no `httpx`, quem levanta é a mesma camada que
    levantaria com a rede fora do ar, e o caminho percorrido é o de produção
    inteiro — incluindo o `try` que envolve a chamada ao SDK.
    """

    class TransporteQueFalha(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise erro

    alvos = _clientes_httpx(transcritor._client)  # noqa: SLF001 - fronteira de transporte
    if not alvos:
        raise unittest.SkipTest("não foi possível alcançar o transporte httpx do deepgram-sdk")

    originais = [(alvo, alvo._transport) for alvo in alvos]  # noqa: SLF001
    for alvo in alvos:
        alvo._transport = TransporteQueFalha()  # noqa: SLF001
    try:
        yield
    finally:
        for alvo, original in originais:
            alvo._transport = original  # noqa: SLF001


class TestTranscricaoIntegracao(unittest.TestCase):
    """TI-06 a TI-10."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.audio = audio_de_referencia()
        cls.silencio = silencio()

    def setUp(self) -> None:
        self.vhs = leitor_vhs()

    def tearDown(self) -> None:
        limpar_overrides()

    def _transcrever(self, transcritor: TranscribeAudio, *, idioma: str = IDIOMA):
        http = cliente({get_transcriber: lambda: transcritor})
        return http.post(f"/api/v1/audio/aud_massa/transcribe?language={idioma}")

    # -- TI-06 ---------------------------------------------------------------

    def test_transcreve_audio_de_referencia(self) -> None:
        """Áudio com fala em português atravessa até o schema de resposta."""
        with self.vhs.fita(chave_stt_da_massa(self.audio, cenario="sucesso")) as fita:
            resposta = self._transcrever(_transcritor_de(self.audio))

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(corpo["audio_id"], "aud_massa")
        self.assertTrue(
            corpo["text"].strip(), "o áudio de referência tem fala; o texto não pode vir vazio"
        )
        self.assertEqual(corpo["language"], "pt-BR")
        self.assertGreater(corpo["duration_seconds"], 0)
        if corpo["confidence"] is not None:
            self.assertGreaterEqual(corpo["confidence"], 0.0)
            self.assertLessEqual(corpo["confidence"], 1.0)

        # A resposta veio da fita, e não de uma chamada nova.
        self.assertEqual(fita.play_count, 1)

    # -- TI-07 ---------------------------------------------------------------

    def test_falha_do_provedor_retorna_502(self) -> None:
        """As três causas de indisponibilidade dão o mesmo `502`, sem vazar SDK.

        A primeira é gravada; as outras duas são simuladas, e a Seção 6.4.3
        registra o motivo: timeout e conexão recusada acontecem sem resposta
        HTTP, e o VCR.py grava interação, não ausência dela.
        """
        for descricao, montar in (
            ("credencial inválida (gravada do provedor)", self._com_credencial_invalida),
            ("provedor inacessível (simulada no transporte)", self._com_conexao_recusada),
            ("tempo limite excedido (simulada no transporte)", self._com_tempo_limite),
        ):
            with self.subTest(causa=descricao):
                resposta = montar()

                self.assertEqual(resposta.status_code, 502)
                corpo = resposta.json()
                self.assertEqual(corpo["error"], "transcription_failed")
                # Nada do provedor pode aparecer no corpo — nem nome de SDK,
                # nem código HTTP interno, nem trecho da exceção.
                for proibido in ("deepgram", "httpx", "401", "timeout", "traceback"):
                    self.assertNotIn(proibido, corpo["message"].lower())

    def _com_credencial_invalida(self):
        """A recusa real do provedor a uma chave deliberadamente errada."""
        with self.vhs.fita(chave_stt_da_massa(self.audio, cenario="credencial-invalida")):
            return self._transcrever(_transcritor_de(self.audio))

    def _com_conexao_recusada(self):
        transcritor = _transcritor_de(self.audio)
        with _transporte_que_levanta(transcritor, httpx.ConnectError("conexão recusada (simulado)")):
            return self._transcrever(transcritor)

    def _com_tempo_limite(self):
        transcritor = _transcritor_de(self.audio)
        with _transporte_que_levanta(transcritor, httpx.ReadTimeout("tempo limite (simulado)")):
            return self._transcrever(transcritor)

    # -- TI-08 ---------------------------------------------------------------

    def test_audio_sem_fala_retorna_texto_vazio(self) -> None:
        """Silêncio não é erro: o provedor devolve 200 com transcrição vazia."""
        with self.vhs.fita(chave_stt_da_massa(self.silencio, cenario="sem-fala")) as fita:
            resposta = self._transcrever(_transcritor_de(self.silencio))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["text"], "")
        self.assertEqual(fita.play_count, 1)

    # -- TI-09 ---------------------------------------------------------------

    def test_idioma_nao_suportado_retorna_422_sem_chamar_provedor(self) -> None:
        """`en-US` é recusado pelo schema, antes de qualquer efeito colateral."""
        transcritor = _transcritor_de(self.audio)
        espiao = _ClienteEspiao(resposta=None)
        transcritor._client = espiao  # noqa: SLF001 - o dublê é o ponto do caso

        resposta = self._transcrever(transcritor, idioma="en-US")

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(
            espiao.chamadas, [], "o provedor não pode ser acionado com idioma inválido"
        )

    # -- TI-10 ---------------------------------------------------------------

    def test_termos_do_dominio_sao_enviados_ao_provedor(self) -> None:
        """Os 12 termos do domínio e o modelo `nova-3` chegam ao SDK.

        Fora do VHS de propósito (Seção 6.4.4): em replay o cliente real nunca é
        acionado, então o replay não diria nada sobre os parâmetros que o código
        de produção monta.
        """
        transcritor = _transcritor_de(self.audio)
        espiao = _ClienteEspiao(resposta=_resposta_deepgram_minima())
        transcritor._client = espiao  # noqa: SLF001 - o dublê é o ponto do caso

        resposta = self._transcrever(transcritor)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(espiao.chamadas), 1)
        argumentos = espiao.chamadas[0]
        self.assertEqual(argumentos["model"], _DEEPGRAM_MODEL)
        self.assertEqual(argumentos["model"], "nova-3")
        self.assertEqual(argumentos["language"], IDIOMA)
        self.assertEqual(list(argumentos["keyterm"]), list(_DOMAIN_KEYTERMS))
        self.assertEqual(len(_DOMAIN_KEYTERMS), 12, "a Seção 6.4.4 fixa doze termos de domínio")


if __name__ == "__main__":
    unittest.main()
