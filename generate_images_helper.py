#!/usr/bin/env python3
"""Build image-generation prompts from input_scripts.json."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from logging_config import configure_logging, log_pipeline_event

logger = logging.getLogger(__name__)

PROMPT_SUFFIX = (
    "vertical 9:16 aspect ratio, cinematic lighting, photorealistic, 4k, "
    "architectural detail, highly detailed"
)


def generate_visual_prompt(text: str) -> str:
    """Generate a visual prompt from a script sentence."""
    clean_text = re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()
    return f"{clean_text}, {PROMPT_SUFFIX}"


def collect_prompts(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn project scripts into per-sentence image prompts."""
    all_prompts: list[dict[str, Any]] = []

    for project in projects:
        project_name = str(project.get("project_name", "Untitled"))
        script_text = str(project.get("script_text", ""))
        sentences = [part.strip() for part in re.split(r"[.!?]", script_text) if part.strip()]

        project_prompts: dict[str, Any] = {"project_name": project_name, "segments": []}
        for index, sentence in enumerate(sentences):
            project_prompts["segments"].append(
                {
                    "index": index,
                    "sentence": sentence,
                    "visual_prompt": generate_visual_prompt(sentence),
                    "output_path": f"temp/{project_name}/img_{index}.png",
                }
            )
        all_prompts.append(project_prompts)

    return all_prompts


def main(
    input_path: str | Path = "input_scripts.json",
    output_path: str | Path = "image_prompts.json",
) -> list[dict[str, Any]]:
    started = time.perf_counter()
    input_file = Path(input_path)
    with open(input_file, encoding="utf-8") as handle:
        projects = json.load(handle)
    if not isinstance(projects, list):
        raise TypeError(f"{input_file} must contain a JSON array")

    all_prompts = collect_prompts(projects)

    output_file = Path(output_path)
    with open(output_file, "w", encoding="utf-8") as handle:
        json.dump(all_prompts, handle, indent=2)

    total_images = sum(len(project["segments"]) for project in all_prompts)
    first_project = str(all_prompts[0]["project_name"]) if all_prompts else "none"
    log_pipeline_event(
        logger,
        "Wrote image prompts",
        project_name=first_project,
        stage="collect_prompts",
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    logger.info("Wrote %s", output_file)
    logger.info("Total projects: %s", len(all_prompts))
    logger.info("Total images needed: %s", total_images)
    return all_prompts


if __name__ == "__main__":
    configure_logging()
    main()
