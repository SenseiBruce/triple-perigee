from pathlib import Path


def test_pyproject_classifiers_declare_a_python_video_cli() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "Topic :: Multimedia :: Video" in text
    assert "Environment :: Console" in text
    assert "triple-perigee" in text
    assert "terraform" not in text.lower()
