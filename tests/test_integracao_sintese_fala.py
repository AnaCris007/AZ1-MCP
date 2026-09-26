"""Síntese de fala e provedor de voz — casos TI-11 a TI-15 (Seção 6.4.4).

A rota `POST /api/v1/text-to-speech` converte a resposta do agente em áudio sob
demanda, acionada pelo botão "Ouvir resposta" da interface. Ela é canal
COMPLEMENTAR: não substitui a apresentação em texto exigida pelo RF01, e por
isso a Seção 6.4.4 a registra sem atribuir-lhe um requisito funcional próprio.

A fronteira sob teste é `GenerateSpeech` → `GeminiSpeechModel` → `google-genai`.
TI-11 a atravessa de verdade, com a fita gravada do provedor; TI-12 a TI-14 não
a atravessam de propósito — e é justamente isso que verificam. A Seção 6.4.1 diz
que a validação de entrada precede sempre o efeito colateral, e o contador do
dublê é o que transforma essa frase em asserção: texto vazio, texto longo demais
e voz não suportada param no serviço ou no schema, sem gastar uma chamada ao
provedor de voz.

Execução:

    python -m unittest tests.test_integracao_sintese_fala -v
"""

from __future__ import annotations

import unittest

from az1_api.dependencies import get_speech_generator
from services.gemini_speech_service import GeminiSpeechModel
from services.speech_service import MAX_SPEECH_TEXT_LENGTH, GenerateSpeech
from tests.apoio_integracao import (
    FRASE,
    MODELO_TTS,
    VOZ,
    chave_tts_da_massa,
    cliente,
    leitor_vhs,
    limpar_overrides,
)


class _ModeloEspiao:
    """Implementa o `SpeechModel` e conta quantas vezes foi acionado.

    O contador é o ponto: TI-12 a TI-14 afirmam que o provedor NÃO é chamado, e
    sem contar não haveria como distinguir "não chamou" de "chamou e o erro veio
    de outro lugar".
    """

    def __init__(self, *, pcm: bytes = b"\x00\x01" * 64, erro: Exception | None = None) -> None:
        self.chamadas: list[tuple[str, str]] = []
        self._pcm = pcm
        self._erro = erro

    def generate_pcm(self, text: str, voice: str) -> bytes:
        self.chamadas.append((text, voice))
        if self._erro is not None:
            raise self._erro
        return self._pcm


class TestSinteseDeFalaIntegracao(unittest.TestCase):
    """TI-11 a TI-15."""

    def tearDown(self) -> None:
        limpar_overrides()

    def _sintetizar(self, gerador: GenerateSpeech, corpo: dict):
        http = cliente({get_speech_generator: lambda: gerador})
        return http.post("/api/v1/text-to-speech", json=corpo)

    def _com_espiao(self, corpo: dict, *, espiao: _ModeloEspiao | None = None):
        espiao = espiao or _ModeloEspiao()
        resposta = self._sintetizar(GenerateSpeech(espiao), corpo)
        return resposta, espiao

    # -- TI-11 ---------------------------------------------------------------

    def test_gera_audio_wav_a_partir_do_texto(self) -> None:
        """Texto típico atravessa até o WAV, com a resposta real do provedor."""
        gerador = GenerateSpeech(
            GeminiSpeechModel.from_api_key("irrelevante-no-replay", MODELO_TTS)
        )

        with leitor_vhs().fita(chave_tts_da_massa()) as fita:
            resposta = self._sintetizar(gerador, {"text": FRASE, "voice": VOZ, "format": "wav"})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.headers["content-type"], "audio/wav")
        self.assertTrue(resposta.content, "o corpo não pode vir vazio")
        # O envelope WAV é montado pelo `pcm_to_wav` do serviço, e não pelo
        # provedor, que devolve PCM cru. Conferir o cabeçalho é conferir que a
        # conversão aconteceu no caminho de produção.
        self.assertTrue(resposta.content.startswith(b"RIFF"))
        self.assertEqual(resposta.content[8:12], b"WAVE")
        self.assertIn("speech.wav", resposta.headers["content-disposition"])
        self.assertEqual(fita.play_count, 1)

    # -- TI-12 ---------------------------------------------------------------

    def test_texto_vazio_nao_aciona_o_provedor(self) -> None:
        """Vazio e só-espaços param no serviço, antes do provedor de voz."""
        for descricao, texto in (("vazio", ""), ("apenas espaços", "   \t\n  ")):
            with self.subTest(texto=descricao):
                resposta, espiao = self._com_espiao({"text": texto})

                self.assertEqual(resposta.status_code, 422)
                self.assertEqual(resposta.json()["error"], "empty_text")
                self.assertEqual(espiao.chamadas, [])

    # -- TI-13 ---------------------------------------------------------------

    def test_texto_acima_do_limite_nao_aciona_o_provedor(self) -> None:
        """Acima de 4000 caracteres, a recusa vem antes da chamada."""
        resposta, espiao = self._com_espiao({"text": "a" * (MAX_SPEECH_TEXT_LENGTH + 1)})

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["error"], "text_too_long")
        self.assertEqual(espiao.chamadas, [])

    def test_texto_no_limite_exato_e_aceito(self) -> None:
        """A fronteira do limite: 4000 caracteres passam, 4001 não.

        Complementa TI-13. Sem este caso, uma troca de `>` por `>=` no serviço
        passaria despercebida — o limite continuaria recusando o que devia, e
        também o que não devia.
        """
        resposta, espiao = self._com_espiao({"text": "a" * MAX_SPEECH_TEXT_LENGTH})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(espiao.chamadas), 1)

    # -- TI-14 ---------------------------------------------------------------

    def test_voz_ou_formato_nao_suportado_retorna_422(self) -> None:
        """Voz e formato fora do catálogo são recusados pelo schema Pydantic.

        A recusa acontece ANTES de a dependência ser resolvida, o que é mais
        cedo ainda do que em TI-12 e TI-13: aqui nem o serviço é alcançado.
        """
        for descricao, corpo in (
            ("voz não suportada", {"text": FRASE, "voice": "Puck", "format": "wav"}),
            ("formato não suportado", {"text": FRASE, "voice": VOZ, "format": "mp3"}),
        ):
            with self.subTest(causa=descricao):
                resposta, espiao = self._com_espiao(corpo)

                self.assertEqual(resposta.status_code, 422)
                self.assertEqual(espiao.chamadas, [])

    # -- TI-15 ---------------------------------------------------------------

    def test_falha_ou_audio_vazio_do_provedor_retorna_502(self) -> None:
        """As duas causas dão o mesmo `502 speech_generation_failed`.

        Áudio vazio é tratado como falha de propósito (Seção 6.4.2): devolver
        200 com um WAV de zero quadro entregaria à interface um player mudo, e
        o usuário não teria como distinguir isso de um problema do próprio
        navegador.
        """
        for descricao, espiao in (
            ("provedor lança exceção", _ModeloEspiao(erro=RuntimeError("provedor fora (simulado)"))),
            ("provedor devolve áudio vazio", _ModeloEspiao(pcm=b"")),
        ):
            with self.subTest(causa=descricao):
                resposta, espiao_usado = self._com_espiao({"text": FRASE}, espiao=espiao)

                self.assertEqual(resposta.status_code, 502)
                corpo = resposta.json()
                self.assertEqual(corpo["error"], "speech_generation_failed")
                self.assertEqual(len(espiao_usado.chamadas), 1, "o provedor foi acionado uma vez")
                for proibido in ("gemini", "runtimeerror", "traceback", "simulado"):
                    self.assertNotIn(proibido, corpo["message"].lower())


if __name__ == "__main__":
    unittest.main()
