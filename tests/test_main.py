from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from main import (
    ProjectSchema,
    VideoAutomationApp,
    VideoAutomationError,
    parse_args,
)


def test_load_input_from_fixture(fixture_input: Path) -> None:
    app = VideoAutomationApp(fixture_input)
    assert len(app.projects) == 1
    assert app.projects[0]["project_name"] == "Test_Lemon"
    assert "lemon" in app.projects[0]["script_text"].lower()
    ProjectSchema.model_validate(app.projects[0])


def test_generate_visual_prompt_exact_string() -> None:
    app = VideoAutomationApp(Path("tests/fixtures/input_scripts.json"))
    sentence = "A red balloon floats over the city."
    expected = (
        "A red balloon floats over the city, vertical 9:16 aspect ratio, portrait composition, "
        "cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
    )
    assert app.generate_visual_prompt(sentence) == expected


def test_load_input_rejects_malformed_project(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps([{"project_name": "Broken"}]), encoding="utf-8")
    with pytest.raises(VideoAutomationError, match="Broken"):
        VideoAutomationApp(bad_file)


def test_load_input_rejects_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "not.json"
    bad_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(VideoAutomationError, match="not valid JSON"):
        VideoAutomationApp(bad_file)


def test_load_input_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VideoAutomationError, match="not found"):
        VideoAutomationApp(tmp_path / "missing.json")


def test_load_input_wraps_oserror_for_unreadable_path(tmp_path: Path) -> None:
    blocked = tmp_path / "as_directory.json"
    blocked.mkdir()
    with pytest.raises(VideoAutomationError, match="Failed to read"):
        VideoAutomationApp(blocked)


def test_load_input_rejects_non_array_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "object.json"
    bad_file.write_text(json.dumps({"project_name": "Nope"}), encoding="utf-8")
    with pytest.raises(VideoAutomationError, match="JSON array"):
        VideoAutomationApp(bad_file)


def test_load_input_rejects_non_object_entry(tmp_path: Path) -> None:
    bad_file = tmp_path / "list.json"
    bad_file.write_text(json.dumps(["not-an-object"]), encoding="utf-8")
    with pytest.raises(VideoAutomationError, match="index 0"):
        VideoAutomationApp(bad_file)


def test_parse_args_defaults_and_overrides() -> None:
    args = parse_args(["--input", "custom.json", "--output-dir", "out", "--temp-dir", "tmp"])
    assert args.input == "custom.json"
    assert args.output_dir == "out"
    assert args.temp_dir == "tmp"


def test_generate_image_asset_wraps_backend_errors(tmp_path: Path, fixture_input: Path) -> None:
    def boom(prompt: str, output_filename: Path) -> None:
        raise RuntimeError("disk full")

    app = VideoAutomationApp(fixture_input, image_generator=boom)
    with pytest.raises(VideoAutomationError, match="Image generation failed"):
        app.generate_image_asset("prompt", tmp_path / "frame.png")


def test_generate_audio_asset_wraps_backend_errors(tmp_path: Path, fixture_input: Path) -> None:
    async def boom(text: str, output_filename: Path) -> None:
        raise RuntimeError("tts down")

    app = VideoAutomationApp(fixture_input, audio_generator=boom)
    with pytest.raises(VideoAutomationError, match="Audio generation failed"):
        asyncio.run(app.generate_audio_asset("hello", tmp_path / "a.wav"))


def test_process_project_rejects_empty_script(tmp_path: Path, fixture_input: Path) -> None:
    app = VideoAutomationApp(fixture_input, output_dir=tmp_path / "out", temp_dir=tmp_path / "temp")
    with pytest.raises(VideoAutomationError, match="no usable sentences"):
        asyncio.run(app.process_project({"project_name": "Empty", "script_text": "..."}))


def test_run_continues_after_a_failed_project(tmp_path: Path) -> None:
    input_file = tmp_path / "mixed.json"
    input_file.write_text(
        json.dumps(
            [
                {"project_name": "Bad", "script_text": "..."},
                {"project_name": "Good", "script_text": "A calm lake at dawn."},
            ]
        ),
        encoding="utf-8",
    )

    async def silent_audio(text: str, output_filename: Path) -> None:
        from tests.media_utils import write_silence_wav

        write_silence_wav(Path(output_filename), duration=0.3)

    def fake_image(prompt: str, output_filename: Path) -> None:
        from tests.media_utils import write_placeholder_png

        write_placeholder_png(Path(output_filename))

    app = VideoAutomationApp(
        input_file,
        image_generator=fake_image,
        audio_generator=silent_audio,
        output_dir=tmp_path / "output",
        temp_dir=tmp_path / "temp",
        audio_extension=".wav",
        video_size=(64, 96),
        fps=8,
    )
    asyncio.run(app.run())
    assert (tmp_path / "output" / "Good.mp4").exists()


def test_apply_ken_burns_interpolates_zoom() -> None:
    app = VideoAutomationApp(Path("tests/fixtures/input_scripts.json"))

    class DummyClip:
        def resize(self, effect):
            self.effect = effect
            return self

    clip = DummyClip()
    result = app.apply_ken_burns(clip, duration=10, zoom_ratio=1.15)
    assert result.effect(0) == pytest.approx(1.0)
    assert result.effect(10) == pytest.approx(1.15)
    assert result.effect(5) == pytest.approx(1.075)
