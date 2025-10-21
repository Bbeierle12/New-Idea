# Contributing to GlyphX

Thanks for your interest in contributing! This guide outlines the standard workflow.

## Prerequisites

- Python 3.10+
- `pip install -e .[dev]` to install dev dependencies
- Familiarity with Tkinter and REST APIs is a plus

## Workflow

1. **Fork & Clone** – Create a feature branch off `main`.
2. **Install deps** – `make install` (creates a venv and installs dev extras).
3. **Run lint/tests** – `make lint` and `make test` (will produce `coverage.xml`).
4. **Keep UI responsive** – Ensure new features run on the background `Worker` if they might block.
5. **Add tests** – Unit tests go in `glyphx/tests/`; prefer Hypothesis for property-style checks.
6. **Document** – Update README/user guide/architecture notes when behaviour changes.
7. **Submit PR** – Reference related issues and detail test coverage in the PR description.

## Coding Guidelines

- Follow the existing module structure (infra/services/gui segregation).
- Keep docstrings up-to-date for public functions/classes.
- Avoid long-running operations on the Tkinter thread.
- Default to ASCII unless the file already uses extended characters.

## Commit Hygiene

- Squash trivial commits where possible.
- Reference issues using `Fixes #123` / `Closes #123` for auto-linking.

## Release Flow

The GitHub Actions release workflow runs `bundle-*` targets for every tag of the form `v*` and uploads artifacts automatically. Coordinate version bumps in `pyproject.toml` before tagging.
