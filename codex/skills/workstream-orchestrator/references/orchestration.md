# Workstream Orchestration Reference

## Workstream keys

- `template-contract-export` -> `autoreport_v0.3-template-contract-export`
- `generic-payload-schema` -> `autoreport_v0.3-generic-payload-schema`
- `text-layout-engine` -> `autoreport_v0.3-text-layout-engine`
- `image-layout-engine` -> `autoreport_v0.3-image-layout-engine`
- `cli-web-template-flow` -> `autoreport_v0.3-cli-web-template-flow`

These worktrees live beside the main repo under the same workspace root.

## Narrow test commands

- `template-contract-export`
  `python -m unittest tests.test_generator tests.test_pptx_writer`
- `generic-payload-schema`
  `python -m unittest tests.test_validator tests.test_loader`
- `text-layout-engine`
  `python -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`
- `image-layout-engine`
  `python -m unittest tests.test_generator tests.test_pptx_writer`
- `cli-web-template-flow`
  `python -m unittest tests.test_cli tests.test_web_app`

Use the shared repo virtualenv at `.\venv\Scripts\python.exe` from the repo
root unless the user explicitly sets another interpreter.

## Merge order

1. `template-contract-export`
2. `generic-payload-schema`
3. `text-layout-engine`
4. `image-layout-engine`
5. `cli-web-template-flow`

`text-layout-engine` and `image-layout-engine` can move in parallel only after
the contract-export and payload-schema surfaces are stable enough.

## Git ownership policy

- Workers own code changes, local tests, and local WIP commits.
- The master thread owns remote push, rebase, merge, and force-push whenever
  the goal is to preserve a clean shared integration history.
- For tracked shared policy changes under files such as `AGENTS.md`,
  `codex/skills/`, or shared architecture docs, the master thread should land
  the change on the shared base first and then propagate it to sibling
  worktrees by rebase.

## Policy sync mode

Use this mode when the master thread changes tracked shared operating rules.

1. Commit and push the policy change on the shared base.
2. Inspect each sibling worktree for local changes.
3. Create a checkpoint commit if the worktree is dirty.
4. Rebase the branch onto `origin/codex/v0.3-template-engine`.
5. Run the branch's narrow verification command.
6. Push the rebased branch.

Do not rely on `.codex/master-next.txt` as the only channel for a new policy
until the affected branches have actually received that policy through git
history.

## Overlap hotspots

- `autoreport/templates/weekly_report.py`
- `autoreport/templates/autofill.py`
- `autoreport/engine/generator.py`
- `tests/test_generator.py`
- `tests/test_pptx_writer.py`

Raise these files explicitly when you see multiple threads changing them at the
same time.

## Instruction file policy

- Write per-thread next steps into `.codex/master-next.txt`.
- Keep these files local/private and out of tracked product docs.
- Overwrite the file with the newest instruction unless the user asks for an
  append-only log.

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
`.pptx` itself when available. Supporting screenshots or exported contract files
are helpful, but they do not replace the final artifact path.

Keep non-committed proof artifacts under `tests/_tmp/` or another clearly local
path. Do not promote proof artifacts into tracked docs or product paths unless
the user explicitly asks for that.
