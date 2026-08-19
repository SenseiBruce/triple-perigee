from pathlib import Path

import pytest

from generate_images_helper import collect_prompts, generate_visual_prompt, main


def test_generate_visual_prompt_exact_string_for_fixed_sentence() -> None:
    sentence = "A red balloon floats over the city."
    expected = (
        "A red balloon floats over the city, vertical 9:16 aspect ratio, "
        "cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
    )
    assert generate_visual_prompt(sentence) == expected


def test_generate_visual_prompt_strips_punctuation() -> None:
    prompt = generate_visual_prompt("Wait—look! It's 2050.")
    assert "," not in prompt.split(",")[0]
    assert "Waitlook Its 2050" in prompt
    assert prompt.endswith(
        "vertical 9:16 aspect ratio, cinematic lighting, photorealistic, 4k, "
        "architectural detail, highly detailed"
    )


def test_collect_prompts_builds_segment_paths() -> None:
    projects = [
        {
            "project_name": "Demo",
            "script_text": "First sentence. Second sentence!",
        }
    ]
    result = collect_prompts(projects)
    assert len(result) == 1
    assert result[0]["project_name"] == "Demo"
    assert len(result[0]["segments"]) == 2
    assert result[0]["segments"][0]["output_path"] == "temp/Demo/img_0.png"
    assert result[0]["segments"][1]["sentence"] == "Second sentence"


def test_main_rejects_non_array_input(tmp_path: Path) -> None:
    bad = tmp_path / "obj.json"
    bad.write_text('{"project_name": "x"}', encoding="utf-8")
    with pytest.raises(TypeError, match="JSON array"):
        main(bad, tmp_path / "out.json")


def test_main_writes_image_prompts_json(tmp_path: Path, fixture_input: Path) -> None:
    output_file = tmp_path / "image_prompts.json"
    result = main(fixture_input, output_file)
    assert output_file.exists()
    assert result[0]["project_name"] == "Test_Lemon"
    assert result[0]["segments"][0]["visual_prompt"].startswith("Picture a bright yellow lemon")
