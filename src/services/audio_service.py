from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum, auto

import av

MAX_DURATION_SECONDS = 5 * 60

AUDIO_FORMAT_CONTENT_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "webm": "audio/webm",
}

_FORMAT_MATCHERS = (
    ("wav", "wav"),
    ("mp3", "mp3"),
    ("mp4", "m4a"),
    ("webm", "webm"),
)

_MAGIC_SIGNATURE_CHECKS = (
    lambda c: c.startswith(b"RIFF") and c[8:12] == b"WAVE",
    lambda c: c.startswith(b"ID3") or c[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"),
    lambda c: c[4:8] == b"ftyp",
    lambda c: c.startswith(b"\x1a\x45\xdf\xa3"),
)


def _looks_like_supported_container(content: bytes) -> bool:
    return any(check(content) for check in _MAGIC_SIGNATURE_CHECKS)


class AudioProbeError(Enum):
    UNSUPPORTED_FORMAT = auto()
    CORRUPTED = auto()


@dataclass
class AudioProbeResult:
    audio_format: str
    duration_seconds: float


def probe_audio(content: bytes) -> AudioProbeResult | AudioProbeError:
    try:
        with av.open(io.BytesIO(content)) as container:
            if container.streams.video or not container.streams.audio:
                return AudioProbeError.UNSUPPORTED_FORMAT

            audio_format = next(
                (fmt for token, fmt in _FORMAT_MATCHERS if token in container.format.name),
                None,
            )
            if audio_format is None:
                return AudioProbeError.UNSUPPORTED_FORMAT

            duration_seconds = _get_duration_seconds(container)
            if duration_seconds is None:
                return AudioProbeError.CORRUPTED

            return AudioProbeResult(audio_format=audio_format, duration_seconds=duration_seconds)
    except (av.error.FFmpegError, OSError):
        if _looks_like_supported_container(content):
            return AudioProbeError.CORRUPTED
        return AudioProbeError.UNSUPPORTED_FORMAT


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
