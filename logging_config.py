"""JSON structured logging for the video pipeline CLI."""

from __future__ import annotations

import logging
import os
import sys

from pythonjsonlogger.json import JsonFormatter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def build_json_formatter() -> JsonFormatter:
    return JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        json_ensure_ascii=False,
        timestamp=True,
    )


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(build_json_formatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))


def log_pipeline_event(
    logger: logging.Logger,
    message: str,
    *,
    project_name: str,
    stage: str,
    duration_ms: float,
) -> None:
    logger.info(
        message,
        extra={
            "project_name": project_name,
            "stage": stage,
            "duration_ms": duration_ms,
        },
    )
