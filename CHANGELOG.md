# Changelog

All notable changes to this project are documented in this file.

## Unreleased

- Classified the project as a Python video CLI (not IaC) via pyproject classifiers.
- Added JSON structured logging with `project_name`, `stage`, and `duration_ms`.
- Committed pip-compile and uv lockfiles; CI installs from the lockfile and runs pip-audit.
- Added docker compose for one-command pipeline runs.

## 0.1.0

- Added a pytest suite, coverage gate, and GitHub Actions CI.
- Made image and audio generation injectable so the pipeline can run without Antigravity.
- Validated `input_scripts.json` with Pydantic and replaced print-based status with logging.
- Pinned dependencies and added a lockfile plus Dependabot.
