from __future__ import annotations

import json
import logging

from logging_config import build_json_formatter, configure_logging, log_pipeline_event


def test_json_formatter_includes_structured_fields() -> None:
    formatter = build_json_formatter()
    record = logging.LogRecord(
        name="main",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Processed segment",
        args=(),
        exc_info=None,
    )
    record.project_name = "Test_Lemon"
    record.stage = "process_segment"
    record.duration_ms = 41.5

    payload = json.loads(formatter.format(record))
    assert payload["project_name"] == "Test_Lemon"
    assert payload["stage"] == "process_segment"
    assert payload["duration_ms"] == 41.5
    assert payload["message"] == "Processed segment"


def test_log_pipeline_event_attaches_expected_extras(caplog) -> None:
    caplog.set_level(logging.INFO)
    logger = logging.getLogger("tests.logging")
    log_pipeline_event(
        logger,
        "Generated TTS audio",
        project_name="Test_Lemon",
        stage="generate_tts_audio",
        duration_ms=12.25,
    )
    assert caplog.records
    record = caplog.records[-1]
    assert record.project_name == "Test_Lemon"
    assert record.stage == "generate_tts_audio"
    assert record.duration_ms == 12.25


def test_configure_logging_emits_json_to_stdout() -> None:
    configure_logging()
    handler = logging.getLogger().handlers[0]
    record = logging.LogRecord("main", logging.INFO, __file__, 1, "hello", (), None)
    payload = json.loads(handler.format(record))
    assert payload["message"] == "hello"
    assert "timestamp" in payload
