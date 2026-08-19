# Video Automation Application

project_type: cli

## Classification

This repository is a **Python CLI / backend video pipeline**, not infrastructure.

- `project_type: cli`
- `detected_frameworks: Docker, Docker Compose, Dev Container, Pydantic`
- Not Terraform, Kubernetes, Helm, Pulumi, or Ansible (`terraform_file_count: 0`, `k8s_manifest_count: 0`)

This is a **Python CLI** for video generation, **not an infrastructure/IaC project**. There is no Terraform, Kubernetes, Helm, Pulumi, or Ansible in this repository. It turns JSON scripts into videos with generated images, human-like text-to-speech, and cinematic Ken Burns effects.

## Features

- 📝 **Script-to-Video**: Convert JSON scripts into professional videos
- 🎨 **Pluggable image generation**: Default placeholder images, or inject your own generator
- 🗣️ **Human-like TTS**: Neural voices via `edge-tts` (no API keys needed)
- 🎬 **Ken Burns Effect**: Smooth zoom animations on images
- 💾 **Memory Optimized**: Sequential processing with temp cleanup
- ✅ **Tested**: Pytest suite with coverage reporting

## Requirements

- Python 3.10+
- FFmpeg (for video encoding)
- 8GB+ RAM recommended

## Installation

Clone into a fresh directory, then:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For a fully pinned install of every transitive dependency:

```bash
pip install -r requirements-lock.txt
```

Install FFmpeg:

```bash
brew install ffmpeg          # macOS
sudo apt-get install ffmpeg  # Debian/Ubuntu
```

Optional environment variables are listed in `.env.example`.

## Dependencies

Runtime packages (`[project.dependencies]` / `requirements.txt`):

- `moviepy==1.0.3`
- `edge-tts==7.2.8`
- `numpy==1.26.4`
- `Pillow==12.3.0`
- `proglog==0.1.12`
- `pydantic==2.13.4`
- `python-json-logger==3.3.0`

Development packages (`[project.optional-dependencies].dev` / `requirements-dev.txt`):

- `pytest==9.1.1`
- `pytest-cov==7.1.0`
- `ruff==0.16.3`
- `pip-audit==2.9.0`
- `pip-tools==7.4.1`
- `mypy==1.13.0`

Install runtime with `pip install -r requirements.txt`. Install the test/lint toolchain with `pip install -r requirements-dev.txt`.

### Docker

From a fresh clone:

```bash
docker compose up --build
```

This builds the image, mounts `tests/fixtures/input_scripts.json`, and writes `output/Test_Lemon.mp4`. Compose uses placeholder audio (`AUDIO_BACKEND=placeholder`) so a fresh clone does not need Microsoft TTS. To use neural voices in Docker, set `AUDIO_BACKEND=edge-tts` and `AUDIO_EXTENSION=.mp3`.

## Tests

Install development dependencies, then run the suite:

```bash
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term
ruff check main.py generate_images_helper.py tests
```

CI runs the same commands on every push and pull request.

## Usage

```bash
python main.py
python main.py --input input_scripts.json --output-dir output
```

This will:
1. Validate `input_scripts.json` against `ProjectSchema`
2. Segment scripts into sentences
3. Generate visual prompts
4. Generate images (placeholder by default, or an injected generator)
5. Generate TTS audio
6. Assemble video with Ken Burns effects
7. Export to `output/` directory

To supply a custom image backend, construct `VideoAutomationApp` with an `image_generator` callable:

```python
from pathlib import Path
from main import VideoAutomationApp


def my_generator(prompt: str, output_filename: Path) -> None: ...


app = VideoAutomationApp("input_scripts.json", image_generator=my_generator)
```

### Input Format

Create an `input_scripts.json` file:

```json
[
  {
    "project_name": "Video_01_History",
    "script_text": "In the year 2050, technology changed everything. Cars began to fly, and the streets went silent."
  }
]
```

### Output

Videos are saved to `output/{project_name}.mp4` with:
- Resolution: 1920x1080 (1080p) by default; override with `VIDEO_WIDTH` / `VIDEO_HEIGHT`
- FPS: 24
- Codec: H.264 (libx264)
- Audio: AAC

## Architecture

See [business-logic.md](business-logic.md) for detailed architecture and data flow diagrams.

## Troubleshooting

### "Image not found" warnings
- The default generator writes a placeholder PNG if no custom generator is injected
- Check that custom generators write to `temp/{project_name}/img_segment_{i}.png`

### Encoding errors
- Verify FFmpeg is installed: `ffmpeg -version`
- Check that FFmpeg supports libx264: `ffmpeg -codecs | grep 264`

## File Structure

```
triple-perigee/
├── main.py                 # Core application
├── generate_images_helper.py
├── logging_config.py       # JSON structured logging
├── requirements.txt        # Direct runtime dependencies
├── requirements-dev.txt    # Pytest, coverage, ruff, pip-audit, pip-tools
├── requirements-lock.txt   # pip-compile lockfile
├── uv.lock                 # uv lockfile
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── tests/                  # Unit and pipeline tests
├── input_scripts.json
├── temp/                   # Temporary assets (auto-deleted)
└── output/                 # Final videos
```

## License

MIT
