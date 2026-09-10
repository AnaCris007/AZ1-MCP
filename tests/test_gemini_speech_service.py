from __future__ import annotations

import unittest
from types import SimpleNamespace

from services.gemini_speech_service import GeminiSpeechModel


class FakeModels:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response: object) -> None:
        self.models = FakeModels(response)


def _response_with(audio: bytes | None) -> object:
    inline_data = SimpleNamespace(data=audio) if audio is not None else None
    part = SimpleNamespace(inline_data=inline_data)
    content = SimpleNamespace(parts=[part])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)])


class TestGeminiSpeechModel(unittest.TestCase):
    def test_envia_texto_modelo_e_voz_ao_sdk(self) -> None:
        client = FakeClient(_response_with(b"pcm"))
        model = GeminiSpeechModel(client=client, model="modelo-tts")

        result = model.generate_pcm("Olá, projeto B", "Kore")

        self.assertEqual(result, b"pcm")
        self.assertEqual(len(client.models.calls), 1)
        call = client.models.calls[0]
        self.assertEqual(call["model"], "modelo-tts")
        self.assertEqual(call["contents"], "Olá, projeto B")
        config = call["config"]
        self.assertEqual(config.response_modalities, ["AUDIO"])
        self.assertEqual(
            config.speech_config.voice_config.prebuilt_voice_config.voice_name,
            "Kore",
        )

    def test_rejeita_resposta_do_gemini_sem_audio(self) -> None:
        model = GeminiSpeechModel(client=FakeClient(_response_with(None)))

        with self.assertRaisesRegex(RuntimeError, "não retornou conteúdo de áudio"):
            model.generate_pcm("Olá", "Kore")


if __name__ == "__main__":
    unittest.main()
