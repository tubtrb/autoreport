---
name: workstream-orchestrator
description: Monitor and orchestrate the autoreport v0.3 parallel worktrees. Use when acting as the master thread to inspect sibling worktrees, verify branch and narrow-test health, decide each thread's next action, and write per-thread instructions into `.codex/master-next.txt`.
---

# Workstream Orchestrator

## Overview

Use this skill for the master-thread role that coordinates the sibling
`autoreport_v0.3-*` worktrees. Keep contract ownership and merge order aligned
while pushing short, concrete next-step instructions into each worktree's
private `.codex/` state. Instruction files stay text-based, while worker
progress and completion reports live in JSON under the same `.codex/` folder.

Master-thread git control is the default operating mode for this skill.
Workers may continue local development, local tests, and local WIP commits, but
the master thread owns checkpoint cleanup, remote push, rebase, merge, and
force-push decisions whenever branch history needs to stay aligned.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../docs/architecture/template-aware-autofill-engine.md`.
- Read `../../../docs/architecture/v0.3-template-workstreams.md`.
- Read `references/orchestration.md`.
- If a thread is about to push, open a PR, or claim public readiness, also read
  `../public-repo-safety/SKILL.md`.

## Workflow

1. Snapshot the sibling worktrees.
- Run the snapshot script before giving instructions.
- Add `--run-tests` when you need fresh health checks rather than relying on the
  last reported result.
- Treat the snapshot as the source for branch status, last commit, and the
  narrow verification command for each thread.

2. Decide the next action per thread.
- Freeze shared contracts before downstream consumers: `template_contract`,
  then `report_payload`, then layout engines, then CLI/web flow.
- Push each branch toward the smallest valuable next milestone: interface
  freeze, conflict reduction, fixture hardening, rebase readiness, or final
  examples.
- Keep ownership boundaries from `v0.3-template-workstreams.md`; do not widen a
  thread just because files overlap.

3. Apply master-owned git orchestration when policy or shared history changes.
- Treat policy updates to tracked shared files such as `AGENTS.md`,
  `codex/skills/`, and shared architecture docs as master-owned changes.
- After a policy change lands on the shared base, the master thread should
  inspect each sibling worktree, make any needed checkpoint commit, rebase onto
  the shared base, rerun the narrow tests, and push the branch.
- Do not assume `.codex/master-next.txt` is the authoritative channel until the
  branch history actually contains the updated skill/policy files.
- Use workers for implementation checkpoints; use the master thread for final
  integration history.

4. Write the next-step instructions.
- Keep each instruction short, concrete, and copy-pastable.
- Default target file is `.codex/master-next.txt` inside each sibling worktree.
- Use the dispatch script with a JSON object that maps workstream keys to
  instruction text.
- Treat `.codex/master-next.txt` as the authoritative per-thread detail
  channel. Put branch-specific priorities, sync notes, review feedback, and
  completion criteria there before asking workers to continue.
- After the per-thread files are written, the normal user-facing follow-up is a
  single shared reminder that tells workers to reload the latest policy/skill
  files and then follow their local `.codex/master-next.txt`.
- Do not make the user manually redistribute long per-thread instructions when
  the same content has already been written into the worktrees.
- Include a functional-evidence requirement, not just a code-status request.
- Require workers to write checkpoint reports into `.codex/worker-status.json`.
- Require workers to write completion reports into `.codex/worker-final.json`
  when the branch is ready for master review.
- Require checkpoint reports to include the input, execution command, output
  artifact path, visible or behavioral result, and remaining gap.
- Require completion reports to include at least one absolute output path that
  the user can open directly for visual verification, such as a generated
  `.pptx`, contract file, skeleton file, or screenshot. Prefer the final
  `.pptx` when available.

5. Collect worker reports before deciding whether a branch is ready.
- Run the report collector after or alongside the git snapshot.
- Treat `.codex/worker-status.json` as the latest checkpoint state and
  `.codex/worker-final.json` as the completion handoff.
- Use the collector output to detect missing reports, stale status updates,
  missing artifact files, or a ready-for-review branch.
- Open `primary_artifact_path` from `worker-final.json` for the final visual
  check instead of relying on tests alone.

6. Report back to the user.
- Summarize which worktrees were inspected, which files were written, and any
  blockers.
- When the instruction files were already updated, prefer giving the user one
  shared broadcast message instead of repeating every branch-specific detail.
- Call out overlap on `autoreport/templates/weekly_report.py`,
  `autoreport/templates/autofill.py`, `autoreport/engine/generator.py`,
  `tests/test_generator.py`, and `tests/test_pptx_writer.py` when relevant.
- Distinguish code health from product evidence. A green test suite is useful,
  but it does not replace a final artifact path that the user can open.

## Interpreter Note

- The shared interpreter lives under the main repo at `.\venv\Scripts\python.exe`
  when commands are run from the main `autoreport` repo root.
- Do not assume sibling worktrees such as `autoreport_v0.3-*` carry their own
  `.venv` directory.
- If you are currently inside a sibling worktree and need to run a shared
  orchestration script, use the main repo interpreter via a relative path such
  as `..\autoreport\venv\Scripts\python.exe` or another confirmed shared
  interpreter path.

## Commands

```bash
.\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\worktree_snapshot.py --run-tests
```

```bash
.\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\collect_worker_reports.py --pretty
```

```bash
@'
{"template-contract-export":"...","generic-payload-schema":"..."}
'@ | .\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\write_master_next.py --stdin-json
```

## Output Contract

- State that `workstream-orchestrator` was used.
- Cite the snapshot, collector output, or narrow test results behind each
  orchestration decision.
- Report each `.codex/master-next.txt` path that was written.
- Distinguish instruction-channel writes from report-channel findings.
