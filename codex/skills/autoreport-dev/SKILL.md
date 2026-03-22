---
name: autoreport-dev
description: Route work in the local autoreport repository to the correct focused skill while keeping changes aligned with the current CLI, schema, PowerPoint, and web contracts.
---

# Autoreport Dev

## Overview

Use this umbrella skill when working anywhere in the `autoreport` repository.
It provides the shared repo frame, keeps current code/tests as the source of truth,
and routes deeper work to one primary focused skill.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../../../README.md` and `../../../pyproject.toml` for the current public frame and package metadata.
- Start with `references/current-repo.md`.
- Identify the primary surface before editing:
  - CLI/entrypoint -> `../autoreport-cli/SKILL.md`
  - Loader/schema/example/tests -> `../report-schema/SKILL.md`
  - Template/generator/writer -> `../pptx-output/SKILL.md`
  - FastAPI/demo HTML/API -> `../web-demo/SKILL.md`
  - README/release/package messaging -> `../release-docs/SKILL.md`
- If a focused skill is missing, continue with this umbrella guidance and report the coverage gap.

## Workflow

1. Ground changes in the current repo.
- Use repository code and tests before relying on roadmap or older local skill copies.
- Treat `codex/skills/` as the shared rule layer and `.codex/` as private/local state.

2. Pick one primary surface.
- Keep one primary skill for the main behavior being changed.
- Only consult adjacent skills when the task crosses subsystem boundaries.

3. Preserve boundaries unless the user asks to redesign them.
- Keep CLI concerns in `autoreport/cli.py`.
- Keep YAML parsing in `autoreport/loader.py`.
- Keep schema rules in `autoreport/validator.py`.
- Keep template shaping in `autoreport/templates/weekly_report.py`.
- Keep orchestration in `autoreport/engine/generator.py`.
- Keep file writing and template compatibility in `autoreport/outputs/pptx_writer.py`.
- Keep web request handling in `autoreport/web/app.py`.

4. Update supporting artifacts together.
- Schema changes should update example YAML and tests.
- User-visible behavior changes should update the nearest tests in the same change.
- Public wording changes should keep README and package metadata aligned with real behavior.

5. Verify narrowly before broadening.
- Run the smallest relevant unittest target first.
- Expand verification only when a change crosses subsystem boundaries.

## Current Constraints

- The repository currently targets weekly report generation only.
- The CLI and web demo both feed the same core generation path.
- Some strings and comments still carry older `v0.1` wording; preserve them unless intentionally updating the contract across code/tests/docs.
- The web demo HTML currently contains tested literal copy from `autoreport/web/app.py`; treat it as contract until deliberately changed.

## Output Contract

- State the primary skill/surface used for the task.
- Cite code/tests as the basis for behavior claims.
- Call out any coverage gap when a focused skill is missing or incomplete.
