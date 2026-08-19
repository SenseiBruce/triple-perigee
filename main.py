from __future__ import annotations

import asyncio
import gc
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Protocol

import edge_tts
import numpy as np

if not hasattr(np, "float"):
    np.float = float  # moviepy 1.0.3 compatibility with NumPy 1.24+

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from pydantic import BaseModel, ValidationError

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
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

class ImageGenerator(Protocol):
    def __call__(self, visual_prompt: str, output_filename: Path) -> None:
        ...


class AudioGenerator(Protocol):
    async def __call__(self, text: str, output_filename: Path) -> None:
        ...


class VideoAutomationError(Exception):
    """Raised when the video automation pipeline cannot continue."""


class ProjectSchema(BaseModel):
    project_name: str
    script_text: str


def generate_placeholder_image(visual_prompt: str, output_filename: Path) -> None:
    """Write a solid 9:16 PNG so the pipeline can run without an external image API."""
    from PIL import Image

    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", VIDEO_SIZE, color=(18, 32, 64))
    image.save(output_path, format="PNG")
    logger.info("Wrote placeholder image to %s (prompt=%s)", output_path, visual_prompt)


async def generate_tts_audio(text: str, output_filename: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_filename))


class VideoAutomationApp:
    def __init__(
        self,
        input_file: str | Path,
        image_generator: ImageGenerator | None = None,
        audio_generator: AudioGenerator | None = None,
        output_dir: Path | None = None,
        temp_dir: Path | None = None,
        audio_extension: str = ".mp3",
        video_size: tuple[int, int] | None = None,
        fps: int | None = None,
    ) -> None:
        self.input_file = Path(input_file)
        self.image_generator = image_generator or generate_placeholder_image
        self.audio_generator = audio_generator or generate_tts_audio
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.temp_dir = Path(temp_dir) if temp_dir is not None else TEMP_DIR
        self.audio_extension = audio_extension
        self.video_size = video_size or VIDEO_SIZE
        self.fps = fps if fps is not None else FPS
        self.projects = self._load_input()

    def _load_input(self) -> list[dict[str, str]]:
        try:
            with open(self.input_file, encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError as exc:
            raise VideoAutomationError(
                f"Input file not found: {self.input_file}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise VideoAutomationError(
                f"Input file is not valid JSON: {self.input_file}"
            ) from exc
        except OSError as exc:
            raise VideoAutomationError(
                f"Failed to read input file {self.input_file}: {exc}"
            ) from exc

        if not isinstance(raw, list):
            raise VideoAutomationError(
                f"Input file {self.input_file} must contain a JSON array of projects"
            )

        projects: list[dict[str, str]] = []
        for index, entry in enumerate(raw):
            try:
                projects.append(ProjectSchema.model_validate(entry).model_dump())
            except ValidationError as exc:
                if isinstance(entry, dict):
                    offending = entry.get("project_name", f"index {index}")
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

    def apply_ken_burns(self, clip: ImageClip, duration: float, zoom_ratio: float = 1.15):
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
        clips_list: list,
    ) -> None:
        combined_text = " ".join(segment_texts)
        logger.info("Processing segment %s: %s", segment_idx + 1, combined_text[:70])

        prompt = self.generate_visual_prompt(combined_text)
        img_path = project_temp_dir / f"img_segment_{segment_idx}.png"
        self.generate_image_asset(prompt, img_path)

        audio_clips_to_combine = [AudioFileClip(str(path)) for path in sentence_audio_paths]
        if not audio_clips_to_combine:
            return

        segment_audio = concatenate_audioclips(audio_clips_to_combine)
        duration = segment_audio.duration

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

    async def process_project(self, project: dict[str, str]) -> Path | None:
        project_name = project["project_name"]
        script_text = project["script_text"]

        logger.info("Processing project: %s", project_name)

        sentences = [part.strip() for part in re.split(r"[.!?]", script_text) if part.strip()]
        if not sentences:
            raise VideoAutomationError(f"Project '{project_name}' has no usable sentences")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        project_temp_dir = self.temp_dir / project_name
        project_temp_dir.mkdir(parents=True, exist_ok=True)

        clips: list = []
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
                duration = temp_clip.duration
                temp_clip.close()

                if current_group_duration + duration > 6.0 and current_group_text:
                    await self.process_segment(
                        current_group_text,
                        current_group_audio_paths,
                        segment_idx,
                        project_temp_dir,
                        clips,
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


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    app = VideoAutomationApp(INPUT_FILE)
    asyncio.run(app.run())
