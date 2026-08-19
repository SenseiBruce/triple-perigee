from __future__ import annotations

import argparse
import asyncio
import gc
import json
import logging
import os
import re
import shutil
import time
import wave
from pathlib import Path
from typing import Any, Protocol

import edge_tts
import numpy as np
from PIL import Image

if not hasattr(np, "float"):
    np.float = float  # type: ignore[attr-defined]
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from pydantic import BaseModel, Field, ValidationError

from logging_config import configure_logging, log_pipeline_event

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "temp"))
VOICE = os.getenv("VOICE", "en-US-ChristopherNeural")
FPS = int(os.getenv("FPS", "24"))
VIDEO_SIZE = (
    int(os.getenv("VIDEO_WIDTH", "1080")),
    int(os.getenv("VIDEO_HEIGHT", "1920")),
)
INPUT_FILE = os.getenv("INPUT_FILE", "input_scripts.json")
AUDIO_BACKEND = os.getenv("AUDIO_BACKEND", "edge-tts")
AUDIO_EXTENSION = os.getenv("AUDIO_EXTENSION", ".mp3")
TTS_RETRIES = int(os.getenv("TTS_RETRIES", "3"))


class ImageGenerator(Protocol):
    def __call__(self, visual_prompt: str, output_filename: Path) -> None: ...


class AudioGenerator(Protocol):
    async def __call__(self, text: str, output_filename: Path) -> None: ...


class VideoAutomationError(Exception):
    """Raised when the video automation pipeline cannot continue."""


class ProjectSchema(BaseModel):
    project_name: str = Field(min_length=1)
    script_text: str = Field(min_length=1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Python CLI that turns JSON scripts into videos. "
            "This is not an infrastructure/IaC project."
        )
    )
    parser.add_argument("--input", default=INPUT_FILE, help="Path to input_scripts.json")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directory for mp4 output")
    parser.add_argument("--temp-dir", default=str(TEMP_DIR), help="Directory for temporary assets")
    parser.add_argument("--voice", default=VOICE, help="edge-tts voice name")
    return parser.parse_args(argv)


def generate_placeholder_image(visual_prompt: str, output_filename: Path) -> None:
    """Write a solid 9:16 PNG so the pipeline can run without an external image API."""
    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", VIDEO_SIZE, color=(18, 32, 64))
    image.save(output_path, format="PNG")
    logger.info("Wrote placeholder image to %s (prompt=%s)", output_path, visual_prompt)


def write_silence_wav(path: Path, duration: float = 0.4, rate: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = max(1, int(duration * rate))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * n_frames)


async def generate_placeholder_audio(text: str, output_filename: Path) -> None:
    started = time.perf_counter()
    write_silence_wav(Path(output_filename))
    log_pipeline_event(
        logger,
        "Generated placeholder audio",
        project_name="unknown",
        stage="generate_placeholder_audio",
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )


async def generate_tts_audio(
    text: str,
    output_filename: Path,
    retries: int = TTS_RETRIES,
    backoff_seconds: float = 0.05,
) -> None:
    started = time.perf_counter()
    last_error: Exception | None = None
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(str(output_filename))
            log_pipeline_event(
                logger,
                "Generated TTS audio",
                project_name="unknown",
                stage="generate_tts_audio",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return
        except Exception as exc:
            last_error = exc
            logger.warning("TTS attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                delay = backoff_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(delay)
    raise VideoAutomationError(f"TTS generation failed after {attempts} attempts") from last_error


def default_audio_generator() -> AudioGenerator:
    if AUDIO_BACKEND == "placeholder":
        return generate_placeholder_audio
    return generate_tts_audio


class VideoAutomationApp:
    def __init__(
        self,
        input_file: str | Path,
        image_generator: ImageGenerator | None = None,
        audio_generator: AudioGenerator | None = None,
        output_dir: Path | None = None,
        temp_dir: Path | None = None,
        audio_extension: str | None = None,
        video_size: tuple[int, int] | None = None,
        fps: int | None = None,
    ) -> None:
        self.input_file = Path(input_file)
        self.image_generator = image_generator or generate_placeholder_image
        self.audio_generator = audio_generator or default_audio_generator()
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.temp_dir = Path(temp_dir) if temp_dir is not None else TEMP_DIR
        self.audio_extension = audio_extension or AUDIO_EXTENSION
        self.video_size = video_size or VIDEO_SIZE
        self.fps = fps if fps is not None else FPS
        self.projects = self._load_input()

    def _load_input(self) -> list[dict[str, str]]:
        try:
            with open(self.input_file, encoding="utf-8") as handle:
                raw: Any = json.load(handle)
        except FileNotFoundError as exc:
            raise VideoAutomationError(f"Input file not found: {self.input_file}") from exc
        except json.JSONDecodeError as exc:
            raise VideoAutomationError(f"Input file is not valid JSON: {self.input_file}") from exc
        except OSError as exc:
            raise VideoAutomationError(
                f"Failed to read input file {self.input_file}: {exc}"
            ) from exc

        if not isinstance(raw, list):
            raise VideoAutomationError(
                f"Input file {self.input_file} must contain a JSON array of projects"
            )
        if len(raw) == 0:
            raise VideoAutomationError(f"Input file {self.input_file} contains no projects")

        projects: list[dict[str, str]] = []
        for index, entry in enumerate(raw):
            try:
                projects.append(ProjectSchema.model_validate(entry).model_dump())
            except ValidationError as exc:
                if isinstance(entry, dict):
                    offending = str(entry.get("project_name", f"index {index}"))
                else:
                    offending = f"index {index}"
                raise VideoAutomationError(
                    f"Invalid project '{offending}' in {self.input_file}: {exc}"
                ) from exc
        return projects

    def generate_visual_prompt(self, text: str) -> str:
        """Parse text into a cinematic image-generation prompt."""
        clean_text = re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()
        return (
            f"{clean_text}, vertical 9:16 aspect ratio, portrait composition, "
            "cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
        )

    def generate_image_asset(self, visual_prompt: str, output_filename: Path) -> None:
        logger.info("Generating image for prompt: %s", visual_prompt)
        try:
            self.image_generator(visual_prompt, Path(output_filename))
        except VideoAutomationError:
            raise
        except Exception as exc:
            raise VideoAutomationError(
                f"Image generation failed for {output_filename}: {exc}"
            ) from exc

    async def generate_audio_asset(self, text: str, output_filename: Path) -> None:
        try:
            await self.audio_generator(text, Path(output_filename))
        except VideoAutomationError:
            raise
        except Exception as exc:
            raise VideoAutomationError(
                f"Audio generation failed for {output_filename}: {exc}"
            ) from exc

    def apply_ken_burns(self, clip: Any, duration: float, zoom_ratio: float = 1.15) -> Any:
        """Apply a smooth Ken Burns (slow zoom) effect to an ImageClip."""

        def effect(t: float) -> float:
            return 1 + (zoom_ratio - 1) * (t / duration)

        return clip.resize(effect)

    async def process_segment(
        self,
        segment_texts: list[str],
        sentence_audio_paths: list[Path],
        segment_idx: int,
        project_temp_dir: Path,
        clips_list: list[Any],
        project_name: str,
    ) -> None:
        started = time.perf_counter()
        combined_text = " ".join(segment_texts)
        logger.info("Processing segment %s: %s", segment_idx + 1, combined_text[:70])

        prompt = self.generate_visual_prompt(combined_text)
        img_path = project_temp_dir / f"img_segment_{segment_idx}.png"
        self.generate_image_asset(prompt, img_path)

        audio_clips_to_combine = [AudioFileClip(str(path)) for path in sentence_audio_paths]
        if not audio_clips_to_combine:
            return

        segment_audio = concatenate_audioclips(audio_clips_to_combine)
        duration = float(segment_audio.duration or 0.0)

        if not img_path.exists():
            logger.warning(
                "Image not found for segment %s: %s. Skipping segment.",
                segment_idx,
                img_path,
            )
            return

        img_clip = ImageClip(str(img_path))

        width, height = img_clip.size
        target_w, target_h = self.video_size
        scale = max(target_w / width, target_h / height)
        img_clip = img_clip.resize(scale)
        img_clip = img_clip.set_position("center")
        img_clip = img_clip.set_duration(duration)

        img_clip = self.apply_ken_burns(img_clip, duration)
        img_clip = img_clip.set_audio(segment_audio)
        img_clip = img_clip.set_fps(self.fps)

        clips_list.append(img_clip)

        for path in sentence_audio_paths:
            if path.exists():
                path.unlink()

        log_pipeline_event(
            logger,
            "Processed segment",
            project_name=project_name,
            stage="process_segment",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def process_project(self, project: dict[str, str]) -> Path | None:
        project_name = project["project_name"]
        script_text = project["script_text"]
        started = time.perf_counter()

        logger.info("Processing project: %s", project_name)

        sentences = [part.strip() for part in re.split(r"[.!?]", script_text) if part.strip()]
        if not sentences:
            raise VideoAutomationError(f"Project '{project_name}' has no usable sentences")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        project_temp_dir = self.temp_dir / project_name
        project_temp_dir.mkdir(parents=True, exist_ok=True)

        clips: list[Any] = []
        current_group_text: list[str] = []
        current_group_audio_paths: list[Path] = []
        current_group_duration = 0.0
        segment_idx = 0
        output_path: Path | None = None

        try:
            for index, sentence in enumerate(sentences):
                temp_sentence_audio = project_temp_dir / f"temp_s_{index}{self.audio_extension}"
                await self.generate_audio_asset(sentence, temp_sentence_audio)

                temp_clip = AudioFileClip(str(temp_sentence_audio))
                duration = float(temp_clip.duration or 0.0)
                temp_clip.close()

                if current_group_duration + duration > 6.0 and current_group_text:
                    await self.process_segment(
                        current_group_text,
                        current_group_audio_paths,
                        segment_idx,
                        project_temp_dir,
                        clips,
                        project_name,
                    )
                    segment_idx += 1
                    current_group_text = [sentence]
                    current_group_audio_paths = [temp_sentence_audio]
                    current_group_duration = duration
                else:
                    current_group_text.append(sentence)
                    current_group_audio_paths.append(temp_sentence_audio)
                    current_group_duration += duration

            if current_group_text:
                await self.process_segment(
                    current_group_text,
                    current_group_audio_paths,
                    segment_idx,
                    project_temp_dir,
                    clips,
                    project_name,
                )

            if clips:
                final_video = concatenate_videoclips(clips, method="compose")
                output_path = self.output_dir / f"{project_name}.mp4"

                logger.info("Exporting video to %s", output_path)
                final_video.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    fps=self.fps,
                    preset="medium",
                    threads=4,
                    logger=None,
                    verbose=False,
                )

                for clip in clips:
                    if clip.audio:
                        clip.audio.close()
                    clip.close()
                final_video.close()
        except VideoAutomationError:
            raise
        except Exception as exc:
            raise VideoAutomationError(
                f"Failed to process project '{project_name}': {exc}"
            ) from exc
        finally:
            if project_temp_dir.exists():
                shutil.rmtree(project_temp_dir)
                logger.info("Cleaned up temp files for %s", project_name)
            gc.collect()

        log_pipeline_event(
            logger,
            "Finished project",
            project_name=project_name,
            stage="process_project",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return output_path

    async def run(self) -> None:
        for project in self.projects:
            try:
                await self.process_project(project)
            except VideoAutomationError:
                logger.exception(
                    "Failed to process project '%s'",
                    project.get("project_name", "unknown"),
                )

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("Final cleanup completed")


def cli_main(argv: list[str] | None = None) -> None:
    configure_logging()
    args = parse_args(argv)
    app = VideoAutomationApp(
        args.input,
        output_dir=Path(args.output_dir),
        temp_dir=Path(args.temp_dir),
    )
    asyncio.run(app.run())


if __name__ == "__main__":
    cli_main()
