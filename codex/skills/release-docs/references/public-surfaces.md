# Public Surfaces

## Main Files

- `README.md`: public project framing, CLI usage, web demo usage, and roadmap.
- `pyproject.toml`: package name, version, description, dependencies, and console entrypoint.
- `docs/posts/autoreport-v<version>-release-notes.md`: versioned release-note source files tracked with the code.
- `examples/autoreport_editorial_template_contract.yaml`: public example template contract.
- `examples/autoreport_editorial_report_payload.yaml`: public example report payload.
- `examples/autoreport_manual_template_contract.yaml`: public manual-template contract example for the hosted web flow.
- `examples/autoreport_manual_report_content.yaml`: public manual draft example for the hosted web flow.
- `examples/report_payload.yaml` and `examples/report_payload.json`: public payload fixtures for validation and interoperability.

## Current Alignment Notes

- README and `pyproject.toml` should stay aligned with the current CLI + web-demo shape described by the code and tests.
- Public examples should stay aligned with the contract-first product surface across the supported editorial and manual built-ins.
- Public docs should describe the manual-first hosted web flow and treat the editorial template as a supported CLI/debug built-in unless the code/tests change.
- Public docs should not imply features that are not present in code/tests.

## Messaging Rules

- Keep top-level product copy focused on what end users and contributors need.
- Keep AI/bootstrap guidance in repo-local contributor files, not in the main product pitch.
