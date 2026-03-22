# AGENTS.md for the `autoreport` repository root

## Scope
- Shared bootstrap entry for this repository.
- Applies to repo-tracked skills under `codex/skills/`.
- Personal state, task tickets, and attestation/proof artifacts stay local under `.codex/`.

## Project Frame
- `autoreport` is currently a deterministic weekly report generator with both CLI and FastAPI web demo entry points.
- The product is user-facing; this file is contributor/bootstrap guidance only.
- Prefer current code and tests over roadmap prose when they differ.

## Source of Truth
- Runtime behavior and error contracts: repository code plus tests.
- Packaging and entrypoint metadata: `pyproject.toml`.
- Public framing and usage examples: `README.md`.
- Example weekly report payload: `examples/weekly_report.yaml`.

## Repo Map
- `autoreport/cli.py`: CLI command parsing and user-visible failure mapping.
- `autoreport/loader.py`, `autoreport/models.py`, `autoreport/validator.py`: YAML loading and strict weekly schema validation.
- `autoreport/templates/weekly_report.py`, `autoreport/engine/generator.py`, `autoreport/outputs/pptx_writer.py`: template shaping, generation orchestration, and `.pptx` writing.
- `autoreport/web/app.py`: public demo HTML and generation API.
- `tests/`: executable contract for CLI, schema, PowerPoint, and web behavior.

## Verification Defaults
- Use the repository virtualenv by default: `.\venv\Scripts\python.exe`
- CLI or entrypoint changes: `.\venv\Scripts\python.exe -m unittest tests.test_cli`
- Loader or schema changes: `.\venv\Scripts\python.exe -m unittest tests.test_loader tests.test_validator`
- Generation or writer changes: `.\venv\Scripts\python.exe -m unittest tests.test_generator tests.test_pptx_writer`
- Web app changes: `.\venv\Scripts\python.exe -m unittest tests.test_web_app`
- Cross-cutting changes: run the narrow focused tests first, then expand to the relevant combination above.

## Generated Artifacts
- Do not commit generated output from `output/`.
- Keep temporary test artifacts under `tests/_tmp/`.
- Keep local bootstrap state under `.codex/`; repo-tracked shared guidance belongs in `codex/`.

## Skill Routing
- Load `codex/skills/autoreport-dev/SKILL.md` first for repository context.
- Then load one primary focused skill based on the main surface being changed:
- CLI, argparse, exit codes, user-visible command output -> `autoreport-cli`
- YAML loading, models, validator rules, example payload, schema tests -> `report-schema`
- Template shaping, generation orchestration, writer behavior, template compatibility -> `pptx-output`
- FastAPI routes, HTML demo surface, API error shape, web tests -> `web-demo`
- README, release notes, packaging metadata, public wording alignment -> `release-docs`
- If a task genuinely spans multiple surfaces, keep one primary skill and consult adjacent skills only where necessary.

## Bootstrap Rules
- When both repo-local and personal/global skills exist, explicitly load the repo-local path under `codex/skills/` and treat it as authoritative for this repository.
- If a focused skill is missing or incomplete, continue with this baseline plus `autoreport-dev` and report the coverage gap instead of hard-failing the session.
- Keep AI/process guidance out of the public product story; do not move bootstrap narrative into `README.md` unless there is an explicit contributor-facing reason.
