from __future__ import annotations

import asyncio
import base64
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from az1_api.dependencies import get_chat_answerer, get_speech_generator, get_token_verifier, get_transcriber
from services.auth_service import AuthError, AuthMode, SupabaseTokenVerifier
from services.chat_service import AnswerChatMessage, ChatReceptionError
from services.speech_service import GenerateSpeech, SpeechGenerationError
from services.transcription_service import TranscribeAudio, TranscriptionError

router = APIRouter(tags=["voice"])

MAX_UTTERANCE_BYTES = 10 * 1024 * 1024


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json({"type": "error", "error": code, "message": message})


@router.websocket("/voice/call")
async def voice_call(
    websocket: WebSocket,
    verifier: SupabaseTokenVerifier = Depends(get_token_verifier),
    transcriber: TranscribeAudio = Depends(get_transcriber),
    answerer: AnswerChatMessage = Depends(get_chat_answerer),
    speech_generator: GenerateSpeech = Depends(get_speech_generator),
) -> None:
    await websocket.accept()
    try:
        start = await websocket.receive_json()
        if start.get("type") != "start_call" or not start.get("conversation_id"):
            await _send_error(websocket, "invalid_start", "Não foi possível iniciar a chamada.")
            await websocket.close(code=1008)
            return

        if verifier.settings.mode is not AuthMode.DISABLED:
            try:
                verifier.verify(start.get("access_token", ""))
            except AuthError:
                await _send_error(websocket, "unauthorized", "Sessão ausente ou inválida.")
                await websocket.close(code=1008)
                return

        conversation_id = start["conversation_id"]
        audio = bytearray()
        await websocket.send_json({"type": "call_ready"})

        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("bytes") is not None:
                audio.extend(message["bytes"])
                if len(audio) > MAX_UTTERANCE_BYTES:
                    audio.clear()
                    await _send_error(websocket, "audio_too_large", "A fala excedeu o limite permitido.")
                continue

            if message.get("text") is None:
                continue
            event = json.loads(message["text"])
            event_type = event.get("type")
            if event_type == "utterance_start":
                audio.clear()
            elif event_type == "end_call":
                await websocket.close(code=1000)
                return
            elif event_type == "utterance_end":
                if not audio:
                    continue
                content = bytes(audio)
                audio.clear()
                try:
                    await websocket.send_json({"type": "transcribing"})
                    transcription = await transcriber.transcribe_content(content=content)
                    text = transcription.text.strip()
                    if not text:
                        await _send_error(websocket, "empty_transcription", "Não identifiquei nenhuma fala.")
                        continue
                    await websocket.send_json({"type": "transcription_final", "text": text})
                    await websocket.send_json({"type": "processing"})
                    reply = await asyncio.to_thread(answerer.answer, text, conversation_id)
                    await websocket.send_json({"type": "agent_response", "text": reply.text})
                    generated = await asyncio.to_thread(speech_generator.generate, reply.text)
                    await websocket.send_json(
                        {
                            "type": "agent_audio",
                            "media_type": generated.media_type,
                            "data": base64.b64encode(generated.content).decode("ascii"),
                        }
                    )
                except TranscriptionError:
                    await _send_error(websocket, "transcription_failed", "Não consegui transcrever sua fala.")
                except ChatReceptionError:
                    await _send_error(websocket, "agent_unavailable", "O agente não conseguiu responder agora.")
                except SpeechGenerationError:
                    await _send_error(websocket, "speech_failed", "Recebi a resposta, mas não consegui gerar o áudio.")
    except (WebSocketDisconnect, json.JSONDecodeError):
        return
