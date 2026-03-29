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
- If the task touches the `v0.3` template-aware direction, also read:
  - `../../../docs/architecture/template-aware-autofill-engine.md`
  - `../../../docs/architecture/web-surface-split.md` when web UX and debug-surface boundaries matter
  - `../../../docs/architecture/v0.3-template-workstreams.md`
- Identify the primary surface before editing:
  - Parallel worktree monitoring/orchestration -> `../workstream-orchestrator/SKILL.md`
  - CLI/entrypoint -> `../autoreport-cli/SKILL.md`
  - Loader/schema/example/tests -> `../report-schema/SKILL.md`
  - Template/generator/writer -> `../pptx-output/SKILL.md`
  - FastAPI/demo HTML/API -> `../web-demo/SKILL.md`
  - Remote deployment handover, EC2 drift checks, public-server mismatch, or entrypoint verification -> `../remote-deployment-handover/SKILL.md`
  - Public repo safety, leak scans, and screenshot hygiene -> `../public-repo-safety/SKILL.md`
  - Release readiness checks, browser smoke tests, and evidence capture -> `../release-verification/SKILL.md`
  - README/release/package messaging -> `../release-docs/SKILL.md`
  - Release backup tags, merged-source-branch cleanup, or refreshing `codex/next` from `main` -> `../release-tagging/SKILL.md`
  - WordPress-style development logs, release notes, and user guides -> `../write-doc-markdown/SKILL.md`
  - Handoff of versioned posts into the private `autorelease` repo -> `../autorelease-handoff/SKILL.md`
- If a focused skill is missing, continue with this umbrella guidance and report the coverage gap.

## Workflow

1. Ground changes in the current repo.
- Use repository code and tests before relying on roadmap or older local skill copies.
- Treat `codex/skills/` as the shared rule layer and `.codex/` as private/local state.

2. Pick one primary surface.
- Keep one primary skill for the main behavior being changed.
- Only consult adjacent skills when the task crosses subsystem boundaries.
- If the turn is acting as the master-thread orchestrator, keep branch-specific
  instructions inside each worktree's `.codex/master-next.txt` and keep the
  user-facing follow-up to one shared broadcast unless the user explicitly asks
  for the branch-by-branch detail.

3. Preserve boundaries unless the user asks to redesign them.
- Keep CLI concerns in `autoreport/cli.py`.
- Keep YAML parsing in `autoreport/loader.py`.
- Keep schema rules in `autoreport/validator.py`.
- Keep template shaping in `autoreport/templates/weekly_report.py`.
- Keep orchestration in `autoreport/engine/generator.py`.
- Keep file writing and template compatibility in `autoreport/outputs/pptx_writer.py`.
- Keep web request handling in `autoreport/web/app.py`.

4. Update supporting artifacts together.
- Contract or payload changes should update the public example files and tests.
- User-visible behavior changes should update the nearest tests in the same change.
- Public wording changes should keep README and package metadata aligned with real behavior.
- When a task supersedes an older contract, homepage flow, helper, example, or copy block, remove the stale predecessor path in the same task instead of leaving both versions behind.
- Treat duplicate old/new paths as blockers unless compatibility is intentional, documented, and covered by tests.
- Use git history and tags for rollback, not tracked dead code kept around "just in case."
- Treat the repo-local skills and `AGENTS.md` as part of the same upkeep set: when behavior or workflow changes, refresh the relevant skill text in the same task instead of leaving bootstrap guidance behind the code.
- If a change affects what a future agent should preload, verify, or consider authoritative, update that guidance before calling the task complete.
- Any task that could make files public should run `public-repo-safety` before signoff.
- If versioned posts under `docs/posts/` are part of the task and the branch is being wrapped up, run `autorelease-handoff` before calling the work finished.

5. Verify narrowly before broadening.
- Run the smallest relevant unittest target first.
- Expand verification only when a change crosses subsystem boundaries.

## Current Constraints

- The public surface is now contract-first and Autoreport-branded, even though some internal module names still mention `weekly_report`.
- The CLI and web demo both feed the same core generation path.
- Some strings and comments still carry older `v0.1` wording; preserve them unless intentionally updating the contract across code/tests/docs.
- The web demo HTML currently contains tested literal copy from `autoreport/web/app.py`; treat it as contract until deliberately changed.

## Current Design Frame

Treat this as living contributor guidance for the `v0.3` direction.
It may evolve as real template workflows are exercised, so keep the paired
architecture docs and focused skills aligned when it changes.

The target template-driven runtime flow is:

1. user selects a PowerPoint template
2. `autoreport` inspects the template and exposes the required YAML or JSON contract
3. a human or another AI fills an `authoring_payload`
4. `autoreport` compiles that into a runtime `report_payload`
5. `autoreport` generates a `.pptx` that follows the selected template

Current design expectations:

- template selection and contract display are first-class product behavior, not just internal debugging helpers
- slide titles should drive the generated `Contents` slide so the outline stays in sync with the real deck
- text and image placement should be template-slot driven, including horizontal and vertical arrangements when the template exposes them
- generalized template contracts, `authoring_payload` scaffolds, compiled runtime payloads, and built-in editorial flows are now the primary product path; legacy weekly-only wording should be treated as migration debt unless tests still lock it
- repo-local skill text should describe the current repo, not a historical snapshot; stale skill guidance should be treated as maintenance debt that blocks accurate future work
- when the design frame changes, update both the architecture docs and the relevant repo-local skill in the same task when practical

## Output Contract

- State the primary skill/surface used for the task.
- Cite code/tests as the basis for behavior claims.
- Call out any coverage gap when a focused skill is missing or incomplete.
- For orchestration turns, say whether `.codex/master-next.txt` was updated and
  use the shared-broadcast pattern rather than restating branch-specific
  instructions in chat unless the user explicitly asks for them.
