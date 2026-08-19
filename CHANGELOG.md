# Changelog

All notable changes to this project are documented in this file.

## Unreleased

- Added a pytest suite, coverage gate, and GitHub Actions CI.
- Made image and audio generation injectable so the pipeline can run without Antigravity.
- Validated `input_scripts.json` with Pydantic and replaced print-based status with logging.
- Pinned dependencies and added a lockfile plus Dependabot.
