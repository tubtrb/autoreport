# Workstream Orchestration Reference

## Discovery model

- Discover active task worktrees from `git worktree list --porcelain`.
- Default branch scope is `codex/v0.3-*`.
- Default exclusions:
  - `codex/v0.3-master`
  - `codex/v0.3-bootstrap-*`
  - `codex/v0.3-salvage-*`
- Any active task worktree may optionally define local orchestration metadata in
  `.codex/workstream.json`.

Suggested local shape:

```json
{
  "key": "web-authoring-ux",
  "test_modules": ["tests.test_web_app"],
  "orchestration_enabled": true
}
```

If local metadata is missing, the scripts should derive the workstream key from
the branch suffix and infer a narrow test recipe from the branch name.

## Retired sibling directory cleanup

- After worktree or branch retirement, the workspace may still contain old
  sibling directories such as `autoreport_v0.3-*`.
- These directories are not authoritative; the git worktree registry is.
- Use `cleanup_retired_worktrees.py` to compare the workspace root against the
  current git worktree list.
- Default cleanup policy:
  - delete retired empty directories automatically
  - report retired non-empty directories as blockers unless the user explicitly
    opts into `--allow-nonempty`
- If a retired empty directory is blocked by `WinError 32` or another Windows
  lock, the first retry step is to ask the user to restart the Codex desktop
  app and then rerun `cleanup_retired_worktrees.py --delete`.
- Keep cleanup scoped to the workspace root so it cannot reach unrelated
  directories.

## Current active task branches

- `codex/v0.3-contract-hardening`
- `codex/v0.3-web-authoring-ux`
- `codex/v0.3-generation-preview`
- `codex/v0.3-release-prep`

These branches may or may not all have live sibling worktrees at a given
moment; orchestration scripts should operate on the discovered worktree set, not
the branch list alone.

## Narrow test defaults

The discovery helper may infer narrow verification commands from branch names:

- `contract*`, `schema*`, `payload*`
  - `python -m unittest tests.test_loader tests.test_validator`
- `web*`, `cli*`
  - `python -m unittest tests.test_cli tests.test_web_app`
- `generation*`, `preview*`, `layout*`, `template*`, `image*`, `text*`
  - `python -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`
- `release*`
  - `python -m unittest tests.test_cli tests.test_web_app`

If a worktree provides `.codex/workstream.json`, its `test_modules` list should
override the inferred default.

Use the shared repo virtualenv at `.\venv\Scripts\python.exe` from the repo
root unless the user explicitly sets another interpreter.

## Merge order

1. `codex/v0.3-contract-hardening`
2. `codex/v0.3-generation-preview`
3. `codex/v0.3-web-authoring-ux`
4. `codex/v0.3-release-prep`

`generation-preview` and `web-authoring-ux` may move in parallel once contract
field names and slot rules are stable enough.

## Stale-code policy

- When a branch changes a public contract, homepage flow, example payload, or
  helper path, master review should look for the superseded predecessor path in
  the touched files.
- Treat stale tracked code, stale sample payloads, stale copy, or duplicate
  old/new product flows as blockers instead of leaving them for a later cleanup
  sweep.
- Apply the same rule to `AGENTS.md` and repo-local skills under `codex/skills/`:
  if the product or workflow changed, bootstrap guidance should move in the same
  task so later agents do not inherit stale repo assumptions.
- The only valid reason to keep both old and new paths is intentional
  compatibility, and that compatibility should be explicit in docs and tests.
- Git history and tags are the rollback mechanism; they are not a reason to
  keep dead code in the live repo.

## Git ownership policy

- Workers own code changes, local tests, and local WIP commits.
- The master thread owns remote push, rebase, merge, and force-push whenever
  the goal is to preserve a clean shared integration history.
- For tracked shared policy changes under files such as `AGENTS.md`,
  `codex/skills/`, or shared architecture docs, the master thread should land
  the change on the shared base first and then propagate it to active task
  worktrees by rebase or forward merges.

## Policy sync mode

Use this mode when the master thread changes tracked shared operating rules.

1. Commit the policy change on `codex/v0.3-master`.
2. Push `codex/v0.3-master`.
3. Run `sync_policy_worktrees.py --base-branch codex/v0.3-master --checkpoint-dirty --push`.
4. Confirm that all active task worktrees either:
   - contain the new base commit and passed their narrow checks, or
   - failed loudly with an explicit blocker in the sync report.
5. Only after that is the policy change considered complete.

Detailed sync sequence:

1. Inspect each active task worktree for local changes.
2. Create a checkpoint commit if the worktree is dirty.
3. Rebase the task branch onto `origin/codex/v0.3-master`.
4. Run the branch's narrow verification command.
5. Push the rebased branch when it already exists remotely or when it has
   unique task commits beyond the base.
   - use `--force-with-lease` for already-remote branches because rebase
     rewrites history
6. Leave branches with no unique commits beyond the base unpushed unless the
   user explicitly wants placeholder remotes.
7. After the sync succeeds, run retired sibling cleanup when old `autoreport_v0.3-*`
   directories remain in the workspace.
8. If cleanup reports an empty retired directory blocked by a Windows lock,
   ask the user to restart the Codex desktop app, then rerun the cleanup step
   before escalating to stronger manual deletion.

Do not consider a policy change "done" while it is only local to a bootstrap or
maintenance branch.

Do not rely on `.codex/master-next.txt` as the only channel for a new policy
until the affected branches have actually received that policy through git
history.

## Overlap hotspots

- `autoreport/template_flow.py`
- `autoreport/models.py`
- `autoreport/validator.py`
- `autoreport/templates/weekly_report.py`
- `autoreport/templates/autofill.py`
- `autoreport/engine/generator.py`
- `autoreport/outputs/pptx_writer.py`
- `autoreport/web/app.py`
- `tests/test_generator.py`
- `tests/test_pptx_writer.py`
- `tests/test_web_app.py`

Raise these files explicitly when you see multiple threads changing them at the
same time.

## Instruction file policy

- Write per-thread next steps into `.codex/master-next.txt`.
- Keep these files local/private and out of tracked product docs.
- Overwrite the file with the newest instruction unless the user asks for an
  append-only log.
- Tell workers to keep `.codex/worker-status.json` current and to create
  `.codex/worker-final.json` only when the branch is ready for master review.
- Treat `.codex/master-next.txt` as the source of truth for branch-specific
  work.
- After updating these files, the shared worker-facing broadcast should stay
  generic: reload the latest policy/skill files, then follow local
  `.codex/master-next.txt`.
- Once valid `.codex/master-next.txt` files exist, new master-thread turns must
  not regenerate or paraphrase branch-specific instructions in user-facing chat
  unless the user explicitly asks for that detail or a worktree is missing its
  instruction file.
- Branch-specific tasks, owned-file lists, and per-branch narrow test commands
  belong in `.codex/master-next.txt` or `.codex/workstream.json`, not in
  repeated chat handoffs.

## Report channel policy

Use JSON as the source of truth for worker reports so the master thread can
collect and validate progress programmatically.

Canonical starter templates live at:

- `references/worker-status.example.json`
- `references/worker-final.example.json`

Workers should copy these shapes instead of inventing ad-hoc keys.

### `.codex/worker-status.json`

Use this file for the latest checkpoint status. Overwrite it at each
checkpoint.

Required fields:

- `workstream_key`
- `branch`
- `head`
- `updated_at`
- `status`
  Allowed values: `in_progress`, `blocked`, `ready_for_review`
- `task_summary`
- `last_green_test_command`
- `working_tree_clean`
- `evidence.input`
- `evidence.command`
- `evidence.artifact_paths`
  Absolute filesystem paths only
- `evidence.visible_result`
- `evidence.remaining_gap`
- `sync_notes`

Required value quality:

- every required string field must be present and non-empty
- `evidence.artifact_paths` must contain at least one absolute path
- every listed artifact path must exist when the report is collected

### `.codex/worker-final.json`

Use this file only when the workstream is ready for master review.

Required fields:

- `workstream_key`
- `branch`
- `head`
- `completed_at`
- `completion_summary`
- `last_green_test_command`
- `primary_artifact_path`
  Absolute filesystem path only
- `artifact_paths`
  Absolute filesystem paths only
- `visible_result`
- `known_gaps`
- `ready_for_master_review`
  Must be `true`

Required value quality:

- every required string field must be present and non-empty
- `artifact_paths` must contain at least one absolute path
- `primary_artifact_path` must be absolute, must exist, and should also appear
  inside `artifact_paths`

## Collector policy

- Run `collect_worker_reports.py` after `worktree_snapshot.py` when you need the
  latest orchestration picture.
- The collector should validate JSON parsing, required fields, absolute paths,
  and artifact existence.
- The collector should reject empty required string fields and empty artifact
  path lists, not just missing keys.
- The collector summary should make these booleans easy to scan per workstream:
  `report_missing`, `status_stale`, `ready_for_review`, `final_present`.
- Final review still requires opening `primary_artifact_path` for visual
  verification.
- Workers should self-check their own handoff before asking for master review:
  `..\autoreport\venv\Scripts\python.exe ..\autoreport\codex\skills\workstream-orchestrator\scripts\collect_worker_reports.py --key <workstream-key> --fail-on-errors --fail-unless-ready --pretty`

## Functional evidence policy

When the user cares about whether the product behavior really works, do not ask
workers to report only code status.

Require each checkpoint report to include:

1. the input used for the check, such as template path, YAML, JSON, or image
2. the execution command
3. the output artifact path
4. the visible or behavioral result
5. the remaining gap

Require each completion report to include at least one absolute filesystem path
that the user can open directly for visual verification. Prefer the generated
`.pptx` itself when available.
