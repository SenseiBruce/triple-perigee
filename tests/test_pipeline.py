from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from main import (
    VideoAutomationApp,
    VideoAutomationError,
    generate_placeholder_audio,
    generate_placeholder_image,
    generate_tts_audio,
)
from tests.media_utils import write_placeholder_png, write_silence_wav


def fake_image_generator(visual_prompt: str, output_filename: Path) -> None:
    write_placeholder_png(Path(output_filename))


async def fake_audio_generator(text: str, output_filename: Path) -> None:
    write_silence_wav(Path(output_filename), duration=0.4)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required to encode video")
def test_process_project_writes_mp4(tmp_path: Path, fixture_input: Path) -> None:
    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    app = VideoAutomationApp(
        fixture_input,
        image_generator=fake_image_generator,
        audio_generator=fake_audio_generator,
        output_dir=output_dir,
        temp_dir=temp_dir,
        audio_extension=".wav",
        video_size=(64, 96),
        fps=8,
    )

    output_path = asyncio.run(app.process_project(app.projects[0]))

    expected = output_dir / "Test_Lemon.mp4"
    assert output_path == expected
    assert expected.exists()
    assert expected.stat().st_size > 0


def test_generate_image_asset_uses_injected_generator(tmp_path: Path, fixture_input: Path) -> None:
    calls: list[tuple[str, Path]] = []

    def recording_generator(prompt: str, output_filename: Path) -> None:
        calls.append((prompt, Path(output_filename)))
        write_placeholder_png(Path(output_filename))

    app = VideoAutomationApp(fixture_input, image_generator=recording_generator)
    target = tmp_path / "frame.png"
    app.generate_image_asset("cinematic lemon", target)

    assert len(calls) == 1
    assert calls[0][0] == "cinematic lemon"
    assert calls[0][1] == target
    assert target.exists()


def test_placeholder_audio_writes_wav(tmp_path: Path) -> None:
    target = tmp_path / "silence.wav"
    asyncio.run(generate_placeholder_audio("ignored", target))
    assert target.exists()
    assert target.stat().st_size > 0


def test_placeholder_image_generator_writes_png(tmp_path: Path) -> None:
    target = tmp_path / "placeholder.png"
    generate_placeholder_image("a quiet harbor at dusk", target)
    assert target.exists()
    assert target.stat().st_size > 0


def test_generate_tts_audio_retries_then_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class FakeCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def save(self, path: str) -> None:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("transient tts failure")
            Path(path).write_bytes(b"ok")

    monkeypatch.setattr("main.edge_tts.Communicate", FakeCommunicate)
    output = tmp_path / "speech.mp3"
    asyncio.run(generate_tts_audio("Hello there.", output, retries=3))
    assert attempts["count"] == 3
    assert output.read_bytes() == b"ok"


def test_generate_tts_audio_raises_after_retries_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class AlwaysFail:
        def __init__(self, text: str, voice: str) -> None:
            pass

        async def save(self, path: str) -> None:
            raise ConnectionError("tts down")

    monkeypatch.setattr("main.edge_tts.Communicate", AlwaysFail)
    with pytest.raises(VideoAutomationError, match="TTS generation failed after 2 attempts"):
        asyncio.run(generate_tts_audio("Hello", tmp_path / "speech.mp3", retries=2))
