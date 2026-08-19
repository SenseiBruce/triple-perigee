from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_input() -> Path:
    return FIXTURES / "input_scripts.json"


@pytest.fixture
def multi_project_input() -> Path:
    return FIXTURES / "multi_projects.json"
