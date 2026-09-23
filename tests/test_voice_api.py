from __future__ import annotations

import base64
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from az1_api.dependencies import (
    get_chat_answerer,
    get_speech_generator,
    get_token_verifier,
    get_transcriber,
)
from az1_api.main import app
from services.auth_service import AuthMode
from services.chat_service import ChatReply
from services.speech_service import GeneratedSpeech
from services.transcription_service import TranscriptionResult


class FakeTranscriber:
    async def transcribe_content(self, *, content: bytes, language: str = "pt-BR") -> TranscriptionResult:
        assert content == b"audio-webm"
        return TranscriptionResult(
            text="Qual é o status do projeto?",
            language=language,
            confidence=0.98,
            duration_seconds=1.2,
        )


class FakeAnswerer:
    def answer(self, message: str, conversation_id: str | None = None) -> ChatReply:
        assert message == "Qual é o status do projeto?"
        assert conversation_id == "conv-voice-1"
        return ChatReply(text="O projeto está em andamento.")


class FakeSpeechGenerator:
    def generate(self, text: str) -> GeneratedSpeech:
        assert text == "O projeto está em andamento."
        return GeneratedSpeech(content=b"wav-audio")


class TestVoiceCallAPI(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_token_verifier] = lambda: SimpleNamespace(
            settings=SimpleNamespace(mode=AuthMode.DISABLED)
        )
        app.dependency_overrides[get_transcriber] = FakeTranscriber
        app.dependency_overrides[get_chat_answerer] = FakeAnswerer
        app.dependency_overrides[get_speech_generator] = FakeSpeechGenerator

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_processa_uma_fala_na_mesma_conexao(self) -> None:
        client = TestClient(app)
        with client.websocket_connect("/api/v1/voice/call") as websocket:
            websocket.send_json({"type": "start_call", "conversation_id": "conv-voice-1"})
            self.assertEqual(websocket.receive_json(), {"type": "call_ready"})

            websocket.send_json({"type": "utterance_start"})
            websocket.send_bytes(b"audio-")
            websocket.send_bytes(b"webm")
            websocket.send_json({"type": "utterance_end"})

            self.assertEqual(websocket.receive_json(), {"type": "transcribing"})
            self.assertEqual(
                websocket.receive_json(),
                {"type": "transcription_final", "text": "Qual é o status do projeto?"},
            )
            self.assertEqual(websocket.receive_json(), {"type": "processing"})
            self.assertEqual(
                websocket.receive_json(),
                {"type": "agent_response", "text": "O projeto está em andamento."},
            )
            audio = websocket.receive_json()
            self.assertEqual(audio["type"], "agent_audio")
            self.assertEqual(base64.b64decode(audio["data"]), b"wav-audio")


if __name__ == "__main__":
    unittest.main()
