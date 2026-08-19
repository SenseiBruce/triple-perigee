from __future__ import annotations

import json
from pathlib import Path

import pytest

from main import ProjectSchema, VideoAutomationApp, VideoAutomationError


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
