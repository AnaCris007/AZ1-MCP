from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import BinaryIO, Protocol
from uuid import uuid4

import av

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_DURATION_SECONDS = 5 * 60

AUDIO_FORMAT_CONTENT_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "webm": "audio/webm",
}

_SIGNATURE_READ_SIZE = 64 * 1024
_M4A_BRANDS = {b"M4A ", b"M4B ", b"isom", b"iso2", b"mp41", b"mp42"}


class AudioStorage(Protocol):
    def store(
        self,
        *,
        key: str,
        content: BinaryIO,
        content_type: str,
        metadata: dict[str, str],
    ) -> None: ...


class AudioProbeError(Enum):
    UNSUPPORTED_FORMAT = auto()
    CORRUPTED = auto()


class AudioReceptionErrorCode(Enum):
    EMPTY_FILE = auto()
    FILE_TOO_LARGE = auto()
    UNSUPPORTED_FORMAT = auto()
    CORRUPTED = auto()
    AUDIO_TOO_LONG = auto()


class AudioReceptionError(Exception):
    def __init__(self, code: AudioReceptionErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class AudioProbeResult:
    audio_format: str
    duration_seconds: float


@dataclass(frozen=True)
class AudioReceipt:
    audio_id: str


class ReceiveAudio:
    def __init__(
        self,
        storage: AudioStorage,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._storage = storage
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def receive(self, content: BinaryIO) -> AudioReceipt:
        file_size = _get_file_size(content)
        if file_size == 0:
            raise AudioReceptionError(AudioReceptionErrorCode.EMPTY_FILE)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise AudioReceptionError(AudioReceptionErrorCode.FILE_TOO_LARGE)

        probe = probe_audio(content)
        if probe is AudioProbeError.UNSUPPORTED_FORMAT:
            raise AudioReceptionError(AudioReceptionErrorCode.UNSUPPORTED_FORMAT)
        if probe is AudioProbeError.CORRUPTED:
            raise AudioReceptionError(AudioReceptionErrorCode.CORRUPTED)
        if probe.duration_seconds > MAX_DURATION_SECONDS:
            raise AudioReceptionError(AudioReceptionErrorCode.AUDIO_TOO_LONG)

        audio_id = f"aud_{self._id_factory()}"
        content.seek(0)
        self._storage.store(
            key=f"incoming/{audio_id}",
            content=content,
            content_type=AUDIO_FORMAT_CONTENT_TYPES[probe.audio_format],
            metadata={"audio-format": probe.audio_format},
        )
        return AudioReceipt(audio_id=audio_id)


def probe_audio(content: BinaryIO) -> AudioProbeResult | AudioProbeError:
    detected_format = _detect_audio_format(content)
    if detected_format is None:
        return AudioProbeError.UNSUPPORTED_FORMAT

    try:
        content.seek(0)
        # UploadFile usa um SpooledTemporaryFile aberto como `w+b`. Sem o modo
        # explícito, o PyAV pode interpretar esse atributo como pedido de saída.
        container = av.open(content, mode="r")
        try:
            if container.streams.video or not container.streams.audio:
                return AudioProbeError.UNSUPPORTED_FORMAT

            duration_seconds = _get_duration_seconds(container)
            if duration_seconds is None or duration_seconds <= 0:
                return AudioProbeError.CORRUPTED

            return AudioProbeResult(audio_format=detected_format, duration_seconds=duration_seconds)
        finally:
            container.close()
    except (av.error.FFmpegError, OSError, ValueError):
        return AudioProbeError.CORRUPTED
    finally:
        content.seek(0)


def _get_file_size(content: BinaryIO) -> int:
    content.seek(0, 2)
    size = content.tell()
    content.seek(0)
    return size


def _detect_audio_format(content: BinaryIO) -> str | None:
    content.seek(0)
    prefix = content.read(_SIGNATURE_READ_SIZE)
    content.seek(0)

    if prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE":
        return "wav"
    if prefix.startswith(b"ID3") or _starts_with_mp3_frame(prefix):
        return "mp3"
    if _has_m4a_brand(prefix):
        return "m4a"
    if prefix.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in prefix[:4096].lower():
        return "webm"
    return None


def _starts_with_mp3_frame(content: bytes) -> bool:
    if len(content) < 2 or content[0] != 0xFF or content[1] & 0xE0 != 0xE0:
        return False
    version_bits = content[1] >> 3 & 0b11
    layer_bits = content[1] >> 1 & 0b11
    return version_bits != 0b01 and layer_bits != 0b00


def _has_m4a_brand(content: bytes) -> bool:
    if len(content) < 16 or content[4:8] != b"ftyp":
        return False

    box_size = int.from_bytes(content[:4], byteorder="big")
    if box_size < 16:
        return False
    box_end = min(box_size, len(content))
    brands = {content[8:12]}
    brands.update(content[offset : offset + 4] for offset in range(16, box_end - 3, 4))
    return bool(brands & _M4A_BRANDS)


def _get_duration_seconds(container: av.container.InputContainer) -> float | None:
    if container.duration is not None:
        return container.duration / av.time_base
    return next(
        (
            float(stream.duration * stream.time_base)
            for stream in container.streams.audio
            if stream.duration is not None
        ),
        None,
    )
