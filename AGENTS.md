# Repository Guidelines

## Project Structure & Module Organization
`care_workflow/` houses the workflow engine (`core.py`) and the `care_blocks/` plugin catalog described in `NAMING.md`. Blocks stay under versioned folders in `transformations/` or `sinks/`, with exports wired through `care_workflow/care_blocks/__init__.py`. Unit tests mirror that layout under `tests/`. Use `examples/` for runnable snippets and `scripts/` for helper bash wrappers such as the MQTT demo.

## Build, Test, and Development Commands
Install dev tooling with `pip install -e ".[dev]"`; use `uv pip install -e ".[dev]"` if you need lockfile reproducibility. Run `python main.py` for the CLI demo. Execute `pytest` for the suite, add `--cov=care_workflow --cov-report=term-missing` before reviews, and prefer `ruff check .` plus `black --check .` for linting. `scripts/test_blocks.sh` boots the plugin and exercises the MQTT sink.

## Coding Style & Naming Conventions
Use 4-space indentation and keep type hints current. Black and Ruff target 100 columns, so trust their autofixes instead of manual formatting. Modules and packages stay `snake_case`, classes `PascalCase`, constants `SCREAMING_SNAKE_CASE`. Block identifiers must follow `care/<name>@vN`, and docstrings stay concise Spanish like the existing core and tests.

## Testing Guidelines
Add tests beside new code: name files `tests/test_<feature>.py` and classes `Test<Subject>` as in `tests/test_core.py`. Cover both success and failure paths, especially around new block metadata or transport errors. Use `pytest -k keyword` while iterating and refresh coverage with `pytest --cov` before requesting review.

## Commit & Pull Request Guidelines
We follow Conventional Commits with optional emoji prefixes (`📚 docs:`, `✨ feat:`) as shown in `git log`. Write imperative summaries, mention the touched subsystem, and split unrelated work. Pull requests must link an issue or explain the motivation, outline the solution, list local validation commands, and attach logs or screenshots for integrations. Confirm lint and tests pass before assigning reviewers.

## Security & Configuration Tips
Never commit credentials or broker endpoints; rely on environment variables or local `.env` files already Git-ignored. Export `WORKFLOWS_PLUGINS=care.workflows.care_steps` when developing custom blocks so Roboflow discovers them, and strip sensitive data from shared JSON payloads. Coordinate with maintainers before introducing new network targets from sink blocks.
