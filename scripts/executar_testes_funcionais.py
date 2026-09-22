"""Campanha funcional controlada: HTTP real em processo, serviços reais e dublês explícitos.

Execute na imagem da API: python scripts/executar_testes_funcionais.py.
Não carrega .env nem usa credenciais corporativas. Saída JSON contém observáveis
por variante; reprovações funcionais dão exit code 1, falhas do instrumento 2.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time
import wave
from importlib.metadata import version
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ["PYTHON_DOTENV_DISABLED"] = "1"

from fastapi.testclient import TestClient
from botocore.exceptions import ClientError

from az1_api.dependencies import (
    get_audio_receiver, get_chat_answerer, get_classificador_de_intencao,
    get_conversa_repository, get_speech_generator, get_transcriber,
    require_authenticated_user,
)
from az1_api.main import app
from rag.retriever import ResultadoBusca
from services.audio_service import ReceiveAudio
from services.auth_service import AuthenticatedUser
from services.chat_service import AnswerChatMessage
from services.conversa_repository import PersistenciaDesligada
from services.gemini_service import GeminiChatModel, RespostaGerada
from services.speech_service import GenerateSpeech
from services.storage_service import S3ObjectStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/evidencias/testes-funcionais"
CONVERSATION_ID = "00000000-0000-4000-8000-000000000001"


def wav(seconds=1, target_size=None):
    output = io.BytesIO()
    with wave.open(output, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(8000)
        file.writeframes(b"\0\0" * int(8000 * seconds))
    data = output.getvalue()
    # PCM real com taxa maior para chegar ao limite sem exceder duração.
    if target_size is not None:
        with wave.open(output := io.BytesIO(), "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(48000)
            file.writeframes(b"\0" * (target_size - 44))
        data = output.getvalue()
    return data


class Model:
    def __init__(self):
        self.calls = 0

    def generate_reply(self, message, *, conversation_id=None):
        self.calls += 1
        return RespostaGerada(texto="Resposta controlada para validar o transporte textual.")


class Speech:
    def __init__(self):
        self.calls = 0

    def generate_pcm(self, text, voice):
        self.calls += 1
        return b"\0\0" * 240


def main():
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    model, speech = Model(), Speech()
    storage = S3ObjectStorage.from_settings(S3StorageSettings(
        bucket_name="az1-functional-test", endpoint_url=os.environ.get("FUNCTIONAL_S3_URL", "http://az1-functional-minio:9000"),
        region_name="us-east-1", access_key="functional-test", secret_key="functional-test-only",
    ))
    try:
        storage._client.create_bucket(Bucket="az1-functional-test")
    except ClientError as error:
        if error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise
    receiver = ReceiveAudio(storage)
    transcriber = TranscribeAudio(storage, "controlled-test-key")
    app.dependency_overrides.update({
        get_audio_receiver: lambda: receiver,
        get_chat_answerer: lambda: AnswerChatMessage(model),
        get_speech_generator: lambda: GenerateSpeech(speech),
        get_transcriber: lambda: transcriber,
        get_conversa_repository: lambda: PersistenciaDesligada("campanha isolada; persistência avaliada na regressão"),
        get_classificador_de_intencao: lambda: None,
        require_authenticated_user: lambda: AuthenticatedUser(subject="functional-test", email="functional@example.com", name="Usuário Sintético", provider="azure"),
    })
    client = TestClient(app, raise_server_exceptions=False)

    def run(case, variant, path, expected_status, expected_error=None, *, data=None, text=None, mime="audio/wav", extra=None):
        before = storage._client.list_objects_v2(Bucket=storage._bucket_name).get("KeyCount", 0)
        calls = model.calls + speech.calls
        if data is not None:
            response = client.post(path, files={"audio": ("fixture.bin", data, mime)})
            entry = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mime": mime}
        else:
            payload = {"message": text, "conversation_id": CONVERSATION_ID} if path.endswith("/chat") else {"text": text}
            response = client.post(path, json=payload)
            entry = {"json": payload} if text is None or len(text) < 200 else {"field": "message" if path.endswith("/chat") else "text", "characters": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        body = response.json() if "json" in response.headers.get("content-type", "") else {"media_type": response.headers.get("content-type"), "bytes": len(response.content)}
        after = storage._client.list_objects_v2(Bucket=storage._bucket_name).get("KeyCount", 0)
        ok = response.status_code == expected_status
        if expected_error:
            ok = ok and body.get("error") == expected_error
        effects = {"new_objects": after - before, "provider_calls": model.calls + speech.calls - calls}
        if data is not None:
            if expected_status == 201:
                stored = storage.fetch(key=f"incoming/{body.get('id')}") if response.status_code == 201 else b""
                effects["stored_sha256"] = hashlib.sha256(stored).hexdigest()
                ok = ok and stored == data and after - before == 1
            else:
                ok = ok and after == before
        if path.endswith("/chat") and expected_status == 200:
            ok = ok and isinstance(body.get("reply"), str) and bool(body["reply"].strip())
        if expected_status == 422 and text is not None:
            ok = ok and effects["provider_calls"] == 0
        if expected_status == 200 and text is not None and path in {"/api/v1/chat", "/api/v1/text-to-speech"}:
            ok = ok and effects["provider_calls"] == 1
        if path == "/api/v1/audio" and expected_status != 201:
            ok = ok and after == before
        if extra:
            ok = ok and extra(body, effects)
        records.append({"case": case, "variant": variant, "method": "POST", "path": path,
                        "input": entry, "expected": {"status": expected_status, "error": expected_error},
                        "observed": {"status": response.status_code, "body": body, "effects": effects},
                        "status": "Aprovado" if ok else "Reprovado", "scope": "API + serviço; MinIO real; autenticação/modelos controlados"})
        return response

    try:
        run("CT-RF01-01", "WAV real (parcial: demais formatos pendentes)", "/api/v1/audio", 201, data=wav())
        run("CT-RF01-06", "assinatura Ogg", "/api/v1/audio", 415, "unsupported_format", data=b"OggS" + b"\0" * 100, mime="audio/ogg")
        run("CT-RF01-07", "12 MiB", "/api/v1/audio", 413, "file_too_large", data=b"\0" * (12 * 1024 * 1024))
        run("CT-RF01-08", "WAV 360 segundos", "/api/v1/audio", 422, "audio_too_long", data=wav(360))
        for variant, data in [("zero byte", b""), ("WAV truncado", b"RIFF\x00\x00\x00\x00WAVE")]:
            run("CT-RF01-09", variant, "/api/v1/audio", 422, "invalid_audio", data=data)
        run("CT-RF01-10", "JSON sem multipart", "/api/v1/audio", 422, text=None)
        run("CT-RF01-11", "objeto inexistente", "/api/v1/audio/aud_inexistente/transcribe", 404, "audio_not_found")
        upload = client.post("/api/v1/audio", files={"audio": ("speech.wav", wav(), "audio/wav")}).json()
        class FailingSTT:
            async def transcribe_file(self, **kwargs):
                raise RuntimeError("controlled-provider-failure")
        transcriber._client = SimpleNamespace(listen=SimpleNamespace(v1=SimpleNamespace(media=FailingSTT())))
        run("CT-RF01-12", "falha injetada no STT; sem cassette VHS", f"/api/v1/audio/{upload['id']}/transcribe", 502, "transcription_failed",
            extra=lambda body, effects: "controlled-provider-failure" not in json.dumps(body))
        for index, text in enumerate(["Status do SYN-01?", "Avanço do SYN-02?", "Prazo do SYN-03?", "Riscos do SYN-04?", "Responsável pelo SYN-05?"]):
            run("CT-RF01-04", f"texto-{index + 1}", "/api/v1/chat", 200, text=text)
        for text in ["", "   "]:
            run("CT-RF01-13", repr(text), "/api/v1/chat", 422, "empty_message", text=text)
        run("CT-RF01-14", "4001 caracteres", "/api/v1/chat", 422, "message_too_long", text="x" * 4001)
        for label, data, status, error in [
            ("10 MiB", wav(target_size=10 * 1024 * 1024), 201, None),
            ("10 MiB + 1 byte", wav(target_size=10 * 1024 * 1024) + b"x", 413, "file_too_large"),
            ("300 segundos", wav(300), 201, None),
            ("300.001 segundos", wav(300.001), 422, "audio_too_long"),
        ]:
            run("CT-RF01-16", label, "/api/v1/audio", status, error, data=data)
        run("CT-RF01-17", "WAV com MIME genérico", "/api/v1/audio", 201, data=wav(), mime="application/octet-stream")
        run("CT-RF01-17", "texto com MIME WAV", "/api/v1/audio", 415, "unsupported_format", data=b"isto nao e audio")
        for text in ["x" * 3999, "x" * 4000, "x" * 4001, "  " + "x" * 4000 + "  ", ""]:
            size = len(text.strip())
            for path, empty, long in [("/api/v1/chat", "empty_message", "message_too_long"), ("/api/v1/text-to-speech", "empty_text", "text_too_long")]:
                error = empty if size == 0 else long if size > 4000 else None
                run("CT-RF01-18", f"{path}: bruto={len(text)}, trim={size}", path, 422 if error else 200, error, text=text)

        # Observável de RF02: modelo real de orquestração, busca instrumentada.
        for case, message in [("CT-RF02-07", "Qual a previsão do tempo em Marte?"), ("CT-RF02-06", "Qual é o avanço do projeto?")]:
            searches = []
            def search(query):
                searches.append(query)
                return []
            gemini = GeminiChatModel(SimpleNamespace(), "controlled", buscar_contexto=search)
            app.dependency_overrides[get_chat_answerer] = lambda: AnswerChatMessage(gemini)
            response = client.post("/api/v1/chat", json={"message": message, "conversation_id": CONVERSATION_ID})
            records.append({"case": case, "variant": "proibição de busca antes da recusa/esclarecimento", "input": message,
                "expected": {"search_calls": 0}, "observed": {"search_calls": len(searches), "status": response.status_code, "body": response.json()},
                "status": "Reprovado" if searches else "Parcial", "scope": "orquestrador Gemini real; recuperação instrumentada; sem modelo externo"})
    finally:
        app.dependency_overrides.clear()
    report = {"started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started, "python": sys.version, "platform": platform.platform(),
        "versions": {package: version(package) for package in ["fastapi", "httpx", "av", "boto3", "deepgram-sdk", "google-genai"]},
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() if (ROOT / ".git").exists() else os.environ.get("TEST_COMMIT", "unknown"),
        "records": records}
    (OUTPUT / "funcionais.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for record in records:
        print(f"{record['case']} | {record['variant']} | {record['status']}")
    return int(any(record["status"] == "Reprovado" for record in records))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(2)
