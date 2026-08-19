from __future__ import annotations

from main import INPUT_FILE, OUTPUT_DIR, parse_args


def test_parse_args_overrides_input_and_output_dir() -> None:
    args = parse_args(["--input", "scripts/custom.json", "--output-dir", "rendered"])
    assert args.input == "scripts/custom.json"
    assert args.output_dir == "rendered"


def test_parse_args_keeps_documented_defaults() -> None:
    args = parse_args([])
    assert args.input == INPUT_FILE
    assert args.output_dir == str(OUTPUT_DIR)
