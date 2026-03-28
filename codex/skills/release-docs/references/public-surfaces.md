# Public Surfaces

## Main Files

- `README.md`: public project framing, CLI usage, web demo usage, and roadmap.
- `pyproject.toml`: package name, version, description, dependencies, and console entrypoint.
- Repo-tracked `release-note-*.md` files: historical release framing for earlier milestones.
- `examples/weekly_report.yaml`: public example payload for the weekly report format.

## Current Alignment Notes

- README and `pyproject.toml` should stay aligned with the current CLI + web-demo shape described by the code and tests.
- The example YAML comment still references `v0.1`.
- Validator error text still references `v0.1` for unsupported `report_type`.
- Public docs should not imply features that are not present in code/tests.

## Messaging Rules

- Keep top-level product copy focused on what end users and contributors need.
- Keep AI/bootstrap guidance in repo-local contributor files, not in the main product pitch.
