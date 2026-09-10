from __future__ import annotations

import unittest

from services.speech_service import (
    MAX_SPEECH_TEXT_LENGTH,
    GenerateSpeech,
    SpeechGenerationError,
    SpeechGenerationErrorCode,
)


class FakeSpeechModel:
    def __init__(self, result: bytes | Exception = b"\x00\x00\x01\x00") -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def generate_pcm(self, text: str, voice: str) -> bytes:
        self.calls.append((text, voice))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class TestGenerateSpeech(unittest.TestCase):
    def test_gera_wav_a_partir_do_pcm(self) -> None:
        model = FakeSpeechModel()
        generator = GenerateSpeech(model=model)

        result = generator.generate("  Olá, mundo!  ", "Kore")

        self.assertEqual(model.calls, [("Olá, mundo!", "Kore")])
        self.assertEqual(result.media_type, "audio/wav")
        self.assertTrue(result.content.startswith(b"RIFF"))
        self.assertIn(b"WAVE", result.content[:16])

    def test_rejeita_texto_vazio_sem_chamar_modelo(self) -> None:
        model = FakeSpeechModel()

        with self.assertRaises(SpeechGenerationError) as ctx:
            GenerateSpeech(model=model).generate("   ")

        self.assertEqual(ctx.exception.code, SpeechGenerationErrorCode.EMPTY_TEXT)
        self.assertEqual(model.calls, [])

    def test_rejeita_texto_muito_longo(self) -> None:
        with self.assertRaises(SpeechGenerationError) as ctx:
            GenerateSpeech(model=FakeSpeechModel()).generate("a" * (MAX_SPEECH_TEXT_LENGTH + 1))

        self.assertEqual(ctx.exception.code, SpeechGenerationErrorCode.TEXT_TOO_LONG)

    def test_converte_falha_do_provedor_em_erro_controlado(self) -> None:
        model = FakeSpeechModel(RuntimeError("credencial secreta"))

        with self.assertRaises(SpeechGenerationError) as ctx:
            GenerateSpeech(model=model).generate("Olá")

        self.assertEqual(ctx.exception.code, SpeechGenerationErrorCode.PROVIDER_FAILED)

    def test_rejeita_resposta_de_audio_vazia(self) -> None:
        with self.assertRaises(SpeechGenerationError) as ctx:
            GenerateSpeech(model=FakeSpeechModel(b"")).generate("Olá")

        self.assertEqual(ctx.exception.code, SpeechGenerationErrorCode.PROVIDER_FAILED)


if __name__ == "__main__":
    unittest.main()

