---
name: autoreport-cli
description: Handle command-line parsing, CLI success/error messaging, exit codes, and entrypoint-facing behavior for the autoreport package.
---

# Autoreport CLI

## Overview

Use this skill for `autoreport/cli.py`, console command behavior, argument parsing,
exit code changes, and user-visible CLI output.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/cli-contract.md`.
- Read `../../../autoreport/cli.py`.
- Read `../../../pyproject.toml` for the `autoreport` console entrypoint.
- Read `../../../tests/test_cli.py`.
- If the change touches generation error mapping, also inspect `../../../autoreport/engine/generator.py` and `../../../autoreport/outputs/pptx_writer.py`.

## Workflow

1. Start from the command contract.
- Confirm parser shape, command names, options, and success output before editing.
- Preserve existing stderr phrasing and exit codes unless the task explicitly changes them.

2. Keep the CLI thin.
- Parse arguments and build `ReportRequest` objects in `cli.py`.
- Do not move loader, validation, template, or writer logic into the CLI layer.

3. Map failures intentionally.
- Keep `1` for expected user/actionable failures.
- Keep `2` for unexpected internal exceptions.
- When new generator/writer errors are surfaced, add explicit mapping rather than relying on a broad catch-all.

4. Update tests with behavior changes.
- Change `tests/test_cli.py` in the same patch whenever success text, failure text, or option behavior changes.

## Current Constraints

- The only CLI subcommand is `generate`.
- `generate` currently accepts a required report path plus optional `--output` and `--template`.
- Success prints `Report generated successfully: <path>`.
- Missing files, template errors, YAML errors, validation errors, and write errors currently exit with code `1`.
- Unexpected uncaught failures currently exit with code `2`.

## Output Contract

- State the CLI contract being preserved or intentionally changed.
- Cite `tests/test_cli.py` for output and exit-code behavior.
