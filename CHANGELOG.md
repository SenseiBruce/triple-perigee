# Changelog

All notable changes to this project are documented in this file.

## 0.2.0

- Added `.repo-meta.json` so classifiers can label this as a Python CLI, not IaC.
- Reject empty `project_name` / `script_text` via Pydantic `Field(min_length=1)`.
- Added schema-validation tests and a multi-project `run()` coverage path.
- Tightened Dependabot to group weekly pip and GitHub Actions updates.

## 0.1.0

- Added a pytest suite, coverage gate, and GitHub Actions CI.
- Made image and audio generation injectable so the pipeline can run without Antigravity.
- Validated `input_scripts.json` with Pydantic and replaced print-based status with logging.
- Pinned dependencies and added a lockfile plus Dependabot.
