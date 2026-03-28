---
name: workstream-orchestrator
description: Monitor and orchestrate the autoreport v0.3 parallel worktrees. Use when acting as the master thread to inspect sibling worktrees, verify branch and narrow-test health, decide each thread's next action, and write per-thread instructions into `.codex/master-next.txt`.
---

# Workstream Orchestrator

## Overview

Use this skill for the master-thread role that coordinates the sibling
`autoreport_v0.3-*` worktrees. Keep contract ownership and merge order aligned
while pushing short, concrete next-step instructions into each worktree's
private `.codex/` state.

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
- Include a functional-evidence requirement, not just a code-status request.
- Require checkpoint reports to name the input, execution command, output
  artifact path, visible/behavioral result, and remaining gap.
- Require completion reports to include at least one absolute output path that
  the user can open directly for visual verification, such as a generated
  `.pptx`, contract file, skeleton file, or screenshot.

5. Report back to the user.
- Summarize which worktrees were inspected, which files were written, and any
  blockers.
- Call out overlap on `autoreport/templates/weekly_report.py`,
  `autoreport/templates/autofill.py`, `autoreport/engine/generator.py`,
  `tests/test_generator.py`, and `tests/test_pptx_writer.py` when relevant.
- Distinguish code health from product evidence. A green test suite is useful,
  but it does not replace a final artifact path that the user can open.

## Commands

```bash
.\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\worktree_snapshot.py --run-tests
```

```bash
@'
{"template-contract-export":"...","generic-payload-schema":"..."}
'@ | .\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\write_master_next.py --stdin-json
```

## Output Contract

- State that `workstream-orchestrator` was used.
- Cite the snapshot or narrow test results behind each orchestration decision.
- Report each `.codex/master-next.txt` path that was written.
