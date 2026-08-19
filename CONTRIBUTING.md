# Contributing

## Setup

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

FFmpeg is required for video export:

```bash
brew install ffmpeg   # macOS
sudo apt-get install ffmpeg   # Debian/Ubuntu
```

## Tests

```bash
pytest --cov=. --cov-report=term
ruff check main.py generate_images_helper.py tests
```

## Pull requests

- Keep each feature or fix in its own commit, including the tests that pin the new behavior.
- Do not mix formatting, refactors, and features in a single commit.
- CI must pass on the pull request before merge.
