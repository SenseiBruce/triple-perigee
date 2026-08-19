import pytest
from pydantic import ValidationError

from main import ProjectSchema


def test_project_schema_accepts_valid_fields() -> None:
    project = ProjectSchema(project_name="Lake", script_text="A calm lake at dawn.")
    assert project.project_name == "Lake"
    assert "lake" in project.script_text.lower()


def test_project_schema_rejects_missing_project_name() -> None:
    with pytest.raises(ValidationError) as exc:
        ProjectSchema.model_validate({"script_text": "A calm lake at dawn."})
    assert "project_name" in str(exc.value)


def test_project_schema_rejects_missing_script_text() -> None:
    with pytest.raises(ValidationError) as exc:
        ProjectSchema.model_validate({"project_name": "Lake"})
    assert "script_text" in str(exc.value)


def test_project_schema_rejects_empty_strings() -> None:
    with pytest.raises(ValidationError):
        ProjectSchema(project_name="", script_text="A calm lake at dawn.")
    with pytest.raises(ValidationError):
        ProjectSchema(project_name="Lake", script_text="")


def test_project_schema_rejects_non_string_fields() -> None:
    with pytest.raises(ValidationError):
        ProjectSchema.model_validate({"project_name": 1, "script_text": "ok"})
    with pytest.raises(ValidationError):
        ProjectSchema.model_validate({"project_name": "Lake", "script_text": ["not", "text"]})
