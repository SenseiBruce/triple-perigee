# Video Automation Application

A modular Python application for MacOS M1 that automates video creation from JSON scripts with AI-generated images, human-like text-to-speech, and cinematic Ken Burns effects.

## Features

- 📝 **Script-to-Video**: Convert JSON scripts into professional videos
- 🎨 **AI Image Generation**: Automatic visual prompt generation and image creation
- 🗣️ **Human-like TTS**: Neural voices via `edge-tts` (no API keys needed)
- 🎬 **Ken Burns Effect**: Smooth zoom animations on images
- 💾 **Memory Optimized**: Designed for 16GB RAM with aggressive cleanup
- 🍎 **M1 Optimized**: ARM64-compatible with efficient encoding

## Requirements

- MacOS M1 (ARM64)
- Python 3.8+
- 16GB RAM
- FFmpeg (for video encoding)

## Installation

### 1. Install FFmpeg
```bash
brew install ffmpeg
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Basic Workflow

The application follows a two-step process:

#### Step 1: Generate Images (via Antigravity)

The `main.py` script includes hooks for image generation, but requires images to be pre-generated. When working with Antigravity:

1. Run the script in "planning mode" to see what images are needed
2. Use Antigravity's `generate_image` tool to create images based on the visual prompts
3. Place images in the appropriate `temp/{project_name}/img_{i}.png` locations

**Automated Workflow (Recommended):**
Create a helper script or use Antigravity automation to generate images before video assembly.

#### Step 2: Run Video Assembly

```bash
python main.py
```

This will:
1. Parse `input_scripts.json`
2. Segment scripts into sentences
3. Generate visual prompts
4. Generate TTS audio
5. Assemble video with Ken Burns effects
6. Export to `output/` directory

### Input Format

Create an `input_scripts.json` file:

```json
[
  {
    "project_name": "Video_01_History",
    "script_text": "In the year 2050, technology changed everything. Cars began to fly, and the streets went silent."
  },
  {
    "project_name": "Video_02_Space",
    "script_text": "The vast emptiness of space is not truly empty. It is filled with dark matter and endless possibilities."
  }
]
```

### Output

Videos are saved to `output/{project_name}.mp4` with:
- Resolution: 1920x1080 (1080p)
- FPS: 24
- Codec: H.264 (libx264)
- Audio: AAC

## Architecture

See [business-logic.md](business-logic.md) for detailed architecture and data flow diagrams.

## Performance

### Memory Management
- Sequential project processing
- Automatic temp file cleanup
- Explicit garbage collection after each project

### Encoding Settings (M1 Optimized)
- Preset: `medium` (balance quality/speed)
- Threads: `4` (optimized for M1 efficiency cores)
- Codec: `libx264` (ARM64 compatible)

### Estimated Processing Time
- Image generation: ~5-10s per segment (depends on tool)
- TTS generation: ~1-2s per segment
- Video encoding: ~30s per minute of final video

## Troubleshooting

### "Image not found" warnings
- Ensure images are generated before running the script
- Check that image paths match `temp/{project_name}/img_{i}.png`

### Memory issues
- Reduce number of projects in `input_scripts.json`
- Lower video resolution in `main.py` (VIDEO_SIZE constant)

### Encoding errors
- Verify FFmpeg is installed: `ffmpeg -version`
- Check that FFmpeg supports libx264: `ffmpeg -codecs | grep 264`

## File Structure

```
triple-perigee/
├── main.py                 # Core application
├── requirements.txt        # Python dependencies
├── business-logic.md       # Architecture documentation
├── README.md              # This file
├── input_scripts.json     # Input data
├── temp/                  # Temporary assets (auto-deleted)
└── output/                # Final videos
```

## Advanced Usage

### Customizing Visual Prompts

Edit the `generate_visual_prompt()` method in `main.py` to customize how text is converted to image prompts.

### Adjusting Ken Burns Effect

Modify the `apply_ken_burns()` method:
- `zoom_ratio`: Default 1.15 (15% zoom)
- Add panning by using `clip.set_position()`

### Changing Voice

Update the `VOICE` constant in `main.py`. Available voices:
- `en-US-ChristopherNeural` (default, male)
- `en-US-JennyNeural` (female)
- `en-GB-RyanNeural` (British male)
- See [edge-tts voices](https://github.com/rany2/edge-tts#usage) for full list

## License

MIT
