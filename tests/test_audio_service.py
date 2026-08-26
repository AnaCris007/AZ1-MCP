from __future__ import annotations

import io
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

import av

from services.audio_service import (
    MAX_DURATION_SECONDS,
    MAX_FILE_SIZE_BYTES,
    AudioProbeError,
    AudioProbeResult,
    AudioReceptionError,
    AudioReceptionErrorCode,
    ReceiveAudio,
    probe_audio,
)


class FakeStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def store(self, **kwargs: object) -> None:
        content = kwargs["content"]
        assert hasattr(content, "read")
        self.calls.append(
            {
                "key": kwargs["key"],
                "content": content.read(),
                "content_type": kwargs["content_type"],
                "metadata": kwargs["metadata"],
            }
        )


class TestReceiveAudio(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = FakeStorage()
        self.receiver = ReceiveAudio(self.storage, id_factory=lambda: "a" * 32)

    def test_rejeita_arquivo_vazio_sem_persistir(self) -> None:
        with self.assertRaisesRegex(AudioReceptionError, "EMPTY_FILE") as context:
            self.receiver.receive(io.BytesIO())

        self.assertEqual(context.exception.code, AudioReceptionErrorCode.EMPTY_FILE)
        self.assertEqual(self.storage.calls, [])

    def test_aceita_arquivo_exatamente_no_limite(self) -> None:
        with patch(
            "services.audio_service.probe_audio",
            return_value=AudioProbeResult("wav", 1),
        ):
            receipt = self.receiver.receive(io.BytesIO(b"x" * MAX_FILE_SIZE_BYTES))

        self.assertEqual(receipt.audio_id, f"aud_{'a' * 32}")
        self.assertEqual(len(self.storage.calls), 1)

    def test_rejeita_arquivo_acima_do_limite_antes_da_sondagem(self) -> None:
        with (
            patch("services.audio_service.probe_audio") as probe,
            self.assertRaisesRegex(AudioReceptionError, "FILE_TOO_LARGE") as context,
        ):
            self.receiver.receive(io.BytesIO(b"x" * (MAX_FILE_SIZE_BYTES + 1)))

        self.assertEqual(context.exception.code, AudioReceptionErrorCode.FILE_TOO_LARGE)
        probe.assert_not_called()
        self.assertEqual(self.storage.calls, [])

    def test_aceita_audio_com_exatamente_cinco_minutos(self) -> None:
        with patch(
            "services.audio_service.probe_audio",
            return_value=AudioProbeResult("mp3", MAX_DURATION_SECONDS),
        ):
            self.receiver.receive(io.BytesIO(b"audio"))

        self.assertEqual(len(self.storage.calls), 1)

    def test_rejeita_audio_acima_de_cinco_minutos(self) -> None:
        with (
            patch(
                "services.audio_service.probe_audio",
                return_value=AudioProbeResult("mp3", MAX_DURATION_SECONDS + 0.001),
            ),
            self.assertRaisesRegex(AudioReceptionError, "AUDIO_TOO_LONG") as context,
        ):
            self.receiver.receive(io.BytesIO(b"audio"))

        self.assertEqual(context.exception.code, AudioReceptionErrorCode.AUDIO_TOO_LONG)
        self.assertEqual(self.storage.calls, [])

    def test_persiste_com_chave_uuid_content_type_e_metadata(self) -> None:
        content = io.BytesIO(b"audio")
        with patch(
            "services.audio_service.probe_audio",
            return_value=AudioProbeResult("m4a", 10),
        ):
            receipt = self.receiver.receive(content)

        self.assertEqual(receipt.audio_id, f"aud_{'a' * 32}")
        self.assertEqual(
            self.storage.calls[0],
            {
                "key": f"incoming/aud_{'a' * 32}",
                "content": b"audio",
                "content_type": "audio/mp4",
                "metadata": {"audio-format": "m4a"},
            },
        )

    def test_converte_erros_da_sondagem_em_erros_do_caso_de_uso(self) -> None:
        cases = (
            (AudioProbeError.UNSUPPORTED_FORMAT, AudioReceptionErrorCode.UNSUPPORTED_FORMAT),
            (AudioProbeError.CORRUPTED, AudioReceptionErrorCode.CORRUPTED),
        )
        for probe_result, expected_error in cases:
            with self.subTest(probe_result=probe_result):
                with (
                    patch("services.audio_service.probe_audio", return_value=probe_result),
                    self.assertRaises(AudioReceptionError) as context,
                ):
                    self.receiver.receive(io.BytesIO(b"audio"))
                self.assertEqual(context.exception.code, expected_error)


class FakeContainer:
    def __init__(self, duration_seconds: float = 1, *, has_video: bool = False) -> None:
        self.duration = int(duration_seconds * av.time_base)
        self.streams = SimpleNamespace(audio=[object()], video=[object()] if has_video else [])
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestProbeAudio(unittest.TestCase):
    def test_sonda_arquivo_wav_real(self) -> None:
        content = io.BytesIO()
        with wave.open(content, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8_000)
            wav_file.writeframes(b"\x00\x00" * 8_000)
        content.seek(0)

        result = probe_audio(content)

        self.assertIsInstance(result, AudioProbeResult)
        assert isinstance(result, AudioProbeResult)
        self.assertEqual(result.audio_format, "wav")
        self.assertAlmostEqual(result.duration_seconds, 1.0, places=3)
        self.assertEqual(content.tell(), 0)

    def test_sonda_spooled_temporary_file_aberto_para_escrita_e_leitura(self) -> None:
        wav_content = io.BytesIO()
        with wave.open(wav_content, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8_000)
            wav_file.writeframes(b"\x00\x00" * 8_000)

        with tempfile.SpooledTemporaryFile(mode="w+b") as upload_file:
            upload_file.write(wav_content.getvalue())
            upload_file.seek(0)
            result = probe_audio(upload_file)

        self.assertIsInstance(result, AudioProbeResult)

    def test_reconhece_os_quatro_formatos_suportados(self) -> None:
        signatures = {
            "wav": b"RIFF\x24\x00\x00\x00WAVEfmt ",
            "mp3": b"ID3\x04\x00\x00\x00\x00\x00\x00",
            "m4a": b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00isom",
            "webm": b"\x1a\x45\xdf\xa3\x42\x82\x84webm",
        }
        for expected_format, signature in signatures.items():
            with self.subTest(expected_format=expected_format):
                container = FakeContainer(duration_seconds=5)
                content = io.BytesIO(signature)
                with patch("services.audio_service.av.open", return_value=container):
                    result = probe_audio(content)

                self.assertEqual(result, AudioProbeResult(expected_format, 5))
                self.assertEqual(content.tell(), 0)
                self.assertTrue(container.closed)

    def test_rejeita_mov_3gp_e_matroska_antes_de_abrir_com_pyav(self) -> None:
        signatures = {
            "mov": b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00",
            "3gp": b"\x00\x00\x00\x14ftyp3gp6\x00\x00\x00\x00",
            "matroska": b"\x1a\x45\xdf\xa3\x42\x82\x88matroska",
        }
        for name, signature in signatures.items():
            with self.subTest(name=name):
                with patch("services.audio_service.av.open") as av_open:
                    result = probe_audio(io.BytesIO(signature))
                self.assertIs(result, AudioProbeError.UNSUPPORTED_FORMAT)
                av_open.assert_not_called()

    def test_classifica_formato_suportado_corrompido(self) -> None:
        with patch("services.audio_service.av.open", side_effect=OSError("corrompido")):
            result = probe_audio(io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt "))
        self.assertIs(result, AudioProbeError.CORRUPTED)

    def test_rejeita_container_com_video(self) -> None:
        with patch(
            "services.audio_service.av.open",
            return_value=FakeContainer(has_video=True),
        ):
            result = probe_audio(io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt "))
        self.assertIs(result, AudioProbeError.UNSUPPORTED_FORMAT)


if __name__ == "__main__":
    unittest.main()
