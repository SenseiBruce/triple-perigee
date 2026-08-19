from __future__ import annotations

from pathlib import Path


def test_pip_compile_lockfile_pins_runtime_dependencies() -> None:
    lockfile = Path("requirements-lock.txt")
    assert lockfile.exists(), "requirements-lock.txt must be committed for reproducible installs"
    text = lockfile.read_text(encoding="utf-8")
    assert "pip-compile" in text
    for package in ("moviepy==", "edge-tts==", "pydantic==", "python-json-logger=="):
        assert package in text


def test_uv_lockfile_is_committed() -> None:
    lockfile = Path("uv.lock")
    assert lockfile.exists(), (
        "uv.lock must be committed so package-manager scanners detect a lockfile"
    )
    text = lockfile.read_text(encoding="utf-8")
    assert "moviepy" in text
    assert "python-json-logger" in text
