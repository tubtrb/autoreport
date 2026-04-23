---
name: parallel-test-planning
description: Monitor a long-running Autoreport verification or release-gate run while building a detailed development plan in parallel. Use when a manual AI regression, release-gate, browser evidence run, or other multi-minute test is still active and Codex should keep checking live artifacts, avoid contaminating the running session, and prepare prioritized fix work or a thread heartbeat automation from the observed failures.
---

# Parallel Test Planning

## Overview

Use this skill when verification is already running and the job is to keep
reading the live evidence while planning the next engineering moves instead of
waiting idle for the test to end.

This is an operations skill, not a product-surface implementation skill. It is
for the period where a run is live, evidence is still arriving, and Codex needs
to separate:

- what the current run has already proven
- what would contaminate that proof
- what code or prompt changes should be prepared next

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../release-verification/SKILL.md`.
- If the live run targets the public web manual flow, also read `../web-demo/SKILL.md`.
- When the run is the manual AI release gate, inspect:
  - `../../../tests/verif_test/release_gate.py`
  - `../../../tests/verif_test/pipeline.py`
  - `../../../autoreport/web/serve.py`
  - `../../../tests/test_web_serve.py`

## Workflow

1. Freeze the active run context first.
- Record the active `run_dir`, run mode, base URL, and whether the public server
  is using reload.
- Treat the current run folder under `output/verif_test/` as immutable evidence.
- If the run already emitted a hard failure, say so plainly before planning
  fixes.

2. Monitor without contaminating the run.
- Prefer reading `events.jsonl`, case artifact folders, process state, and
  health endpoints.
- Do not restart the local server, replace the listening process, modify the run
  directory, or interfere with the live ChatGPT/browser session while the run is
  still being used as evidence.
- Local source edits may be prepared in parallel only when the live server is a
  non-reloading process. Those edits do not affect the current run until the
  server is restarted.
- If the live server is running with reload enabled, treat source edits as
  potentially contaminating and pause code changes until the run finishes.

3. Build the development plan from observed evidence, not guesses.
- Group failures by stage: transport, YAML extract, checker, generate, PPTX
  inspection, or visual review.
- Separate immediate blockers from follow-up cleanup.
- For each candidate fix, identify:
  - the likely root cause
  - the code or prompt surface to change
  - the narrowest validating test
  - the rerun scope needed after the fix
- Prefer plans that explain why the checker and generate stages might disagree
  instead of treating every failure as an isolated bug.

4. Use heartbeat automation when the user wants ongoing monitoring.
- Attach a heartbeat automation to the current thread.
- Poll on a practical interval for the active run, usually every 5 to 15
  minutes.
- Post updates only when there is new progress, a new failure class, or the run
  finishes.
- When the run finishes, post one final summary plus the detailed prioritized
  development plan for the next coding turn.

5. Keep the final status explicit.
- State whether the current run is still active, already failed, or fully
  finished.
- Distinguish stable facts from working hypotheses.
- Call out any prepared code change that was intentionally not activated against
  the live run.

## Current Repo Facts

- The manual AI release gate prepares its samples once at run start, then
  executes the fixed chunk plan from memory.
- The public local server defaults to no reload unless `--reload` is passed.
- The `http` release-gate path talks to the existing server on `127.0.0.1:8000`
  instead of importing the app in-process.

## Output Contract

- State that `parallel-test-planning` was used.
- Name the active run directory and whether it is still live.
- Summarize newly observed failures or completions since the last check.
- Provide a prioritized development plan with concrete code targets and narrow
  validation commands.
