---
name: workstream-orchestrator
description: Monitor and orchestrate active autoreport versioned task worktrees. Use when acting as the master thread to inspect discovered sibling worktrees, verify branch and narrow-test health, decide each thread's next action, and write per-thread instructions into `.codex/master-next.txt`.
---

# Workstream Orchestrator

## Overview

Use this skill for the master-thread role that coordinates the active
`codex/v<version>-*` task worktrees. Keep contract ownership and merge order aligned
while pushing short, concrete next-step instructions into each worktree's
private `.codex/` state. Instruction files stay text-based, while worker
progress and completion reports live in JSON under the same `.codex/` folder.

By default, the orchestration scripts should infer the active `<version>` from
the checked-out `codex/v<version>-master` branch when possible, or else from
the highest discovered version-master branch in the repo.

Master-thread git control is the default operating mode for this skill.
Workers may continue local development, local tests, and local WIP commits, but
the master thread owns checkpoint cleanup, remote push, rebase, merge, and
force-push decisions whenever branch history needs to stay aligned.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../docs/architecture/template-aware-autofill-engine.md`.
- Read `../../../docs/architecture/template-workstreams.md`.
- Read `references/orchestration.md`.
- If a thread is about to push, open a PR, or claim public readiness, also read
  `../public-repo-safety/SKILL.md`.

## Workflow

1. Snapshot the active task worktrees.
- Run the snapshot script before giving instructions.
- Add `--run-tests` when you need fresh health checks rather than relying on the
  last reported result.
- Treat the snapshot as the source for branch status, last commit, and the
  narrow verification command for each thread.
- The script should discover active task worktrees from `git worktree list`
  instead of relying on a fixed folder list.

2. Decide the next action per thread.
- Freeze shared contracts before downstream consumers: `template_contract`,
  then `report_payload`, then layout engines, then CLI/web flow.
- Push each branch toward the smallest valuable next milestone: interface
  freeze, conflict reduction, fixture hardening, rebase readiness, or final
  examples.
- Keep ownership boundaries from `template-workstreams.md`; do not widen a
  thread just because files overlap.
- Before calling a branch ready or landing it on master, scan its touched
  surfaces for stale predecessor code, stale homepage copy, stale examples, or
  duplicate old/new flows left behind by the change.
- Treat leftover tracked code trash as a blocker unless the old path is an
  intentional compatibility surface with explicit tests.
- In the same review pass, check whether the touched behavior changed the
  repository bootstrap story in `AGENTS.md` or the relevant repo-local skill.
- Treat stale tracked skill guidance as a blocker for landing, because the next
  agent turn will inherit those wrong assumptions even if the code itself is
  correct.

3. Apply master-owned git orchestration when policy or shared history changes.
- Treat policy updates to tracked shared files such as `AGENTS.md`,
  `codex/skills/`, and shared architecture docs as master-owned changes.
- A policy change is not complete just because it is committed locally. The
  strict completion bar is:
  - the change is committed on the active `codex/v<version>-master` base
  - that version-master base is pushed
  - the policy sync script has rebased the active task worktrees onto the
    pushed base and rerun their narrow checks
- After a policy change lands on the shared base, use the policy sync script to
  inspect each active task worktree, make any needed checkpoint commit, rebase
  onto the shared base, rerun the narrow tests, and push the branch when
  appropriate.
- When a task branch already exists on origin, the sync push should use
  `--force-with-lease` rather than a plain push because the branch history has
  just been rewritten by rebase.
- Do not assume `.codex/master-next.txt` is the authoritative channel until the
  branch history actually contains the updated skill/policy files.
- Use workers for implementation checkpoints; use the master thread for final
  integration history.

4. Clean retired sibling directories after branch/worktree retirement.
- When old `autoreport_v<version>-*` sibling directories are left behind after a
  branch or worktree is removed, treat their cleanup as master-owned hygiene.
- Use the cleanup script to compare the workspace root against the current git
  worktree registry.
- Delete retired directories only after confirming they are no longer active
  worktrees.
- By default, only empty retired directories should be removed automatically.
  Non-empty retired directories should be surfaced as blockers unless the user
  explicitly wants the stronger cleanup mode.
- If cleanup fails because Windows reports a directory lock against an otherwise
  empty retired sibling, pause and ask the user to restart the Codex desktop
  app first, then rerun the cleanup script before trying stronger manual
  deletion steps.

5. Write the next-step instructions.
- Keep each instruction short, concrete, and copy-pastable.
- Default target file is `.codex/master-next.txt` inside each active task worktree.
- Use the dispatch script with a JSON object that maps workstream keys to
  instruction text.
- Treat `.codex/master-next.txt` as the authoritative per-thread detail
  channel. Put branch-specific priorities, sync notes, review feedback, and
  completion criteria there before asking workers to continue.
- After the per-thread files are written, the normal user-facing follow-up must
  be a single shared reminder that tells workers to reload the latest
  policy/skill files and then follow their local `.codex/master-next.txt`.
- Do not make the user manually redistribute long per-thread instructions when
  the same content has already been written into the worktrees.
- Do not restate branch-specific tasks, owned-file lists, or per-branch narrow
  test commands in user-facing chat unless the user explicitly asks for them or
  a worktree is missing its `.codex/master-next.txt`.
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

6. Collect worker reports before deciding whether a branch is ready.
- Run the report collector after or alongside the git snapshot.
- Treat `.codex/worker-status.json` as the latest checkpoint state and
  `.codex/worker-final.json` as the completion handoff.
- Use the collector output to detect missing reports, stale status updates,
  missing artifact files, or a ready-for-review branch.
- Open `primary_artifact_path` from `worker-final.json` for the final visual
  check instead of relying on tests alone.
- Workers should start from the canonical example JSON files in
  `references/worker-status.example.json` and
  `references/worker-final.example.json` rather than inventing new key shapes.
- Before a worker claims `ready_for_review`, have them rerun the collector for
  their own workstream with a strict command such as:
  `..\autoreport\venv\Scripts\python.exe ..\autoreport\codex\skills\workstream-orchestrator\scripts\collect_worker_reports.py --key <workstream-key> --fail-on-errors --fail-unless-ready --pretty`
- Treat collector contract errors as blockers for handoff, not as optional
  post-review cleanup.

7. Report back to the user.
- Summarize which worktrees were inspected, which files were written, and any
  blockers.
- When the instruction files were already updated, give the user one shared
  broadcast message instead of repeating every branch-specific detail.
- On later master-thread turns, if valid `.codex/master-next.txt` files are
  already present, continue using the shared-broadcast pattern and report only
  deltas, blockers, or requests for missing detail.
- Call out overlap on `autoreport/templates/weekly_report.py`,
  `autoreport/templates/autofill.py`, `autoreport/engine/generator.py`,
  `tests/test_generator.py`, and `tests/test_pptx_writer.py` when relevant.
- Call out stale predecessor code or duplicate old/new product surfaces as
  blockers instead of deferring them to a later cleanup pass.
- Call out stale agent or repo-local skill guidance the same way, rather than
  treating it as optional documentation polish.
- Distinguish code health from product evidence. A green test suite is useful,
  but it does not replace a final artifact path that the user can open.

## Interpreter Note

- The shared interpreter lives under the main repo at `.\venv\Scripts\python.exe`
  when commands are run from the main `autoreport` repo root.
- Do not assume sibling worktrees such as `autoreport_v<version>-*` carry their own
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
.\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\sync_policy_worktrees.py --checkpoint-dirty --push --pretty
```

```bash
.\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\cleanup_retired_worktrees.py --delete --pretty
```

```bash
@'
{"contract-hardening":"...","web-authoring-ux":"..."}
'@ | .\venv\Scripts\python.exe codex\skills\workstream-orchestrator\scripts\write_master_next.py --stdin-json
```

## Output Contract

- State that `workstream-orchestrator` was used.
- Cite the snapshot, collector output, or narrow test results behind each
  orchestration decision.
- Report each `.codex/master-next.txt` path that was written.
- Distinguish instruction-channel writes from report-channel findings.
