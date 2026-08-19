from __future__ import annotations

import wave
from pathlib import Path

from PIL import Image


def write_silence_wav(path: Path, duration: float = 0.4, rate: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = max(1, int(duration * rate))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * n_frames)


def write_placeholder_png(path: Path, size: tuple[int, int] = (64, 96)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(20, 80, 160)).save(path, format="PNG")
