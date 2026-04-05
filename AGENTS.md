# AGENTS.md for the `autoreport` repository root

## Scope
- Shared bootstrap entry for this repository.
- Applies to repo-tracked skills under `codex/skills/`.
- Personal state, task tickets, and attestation/proof artifacts stay local under `.codex/`.

## Project Frame
- `autoreport` is currently a deterministic contract-first PowerPoint deck generator with CLI, a user-facing FastAPI app, and a separate developer-facing debug FastAPI app.
- The product is user-facing; this file is contributor/bootstrap guidance only.
- Prefer current code and tests over roadmap prose when they differ.

## Source of Truth
- Runtime behavior and error contracts: repository code plus tests.
- Packaging and entrypoint metadata: `pyproject.toml`.
- Public framing and usage examples: `README.md`.
- Public server info for release-facing docs, homepage copy, and autorelease handoff: `docs/deployment/public-service-info.yaml`.
- Public contract examples: `examples/autoreport_editorial_template_contract.yaml`, `examples/autoreport_editorial_report_content.yaml`, `examples/autoreport_editorial_authoring_payload.yaml`, `examples/autoreport_editorial_report_payload.yaml`.

## Repo Map
- `autoreport/cli.py`: CLI command parsing and user-visible failure mapping.
- `autoreport/loader.py`, `autoreport/models.py`, `autoreport/validator.py`: YAML loading, contract models, and payload validation.
- `autoreport/template_flow.py`, `autoreport/templates/weekly_report.py`, `autoreport/engine/generator.py`, `autoreport/outputs/pptx_writer.py`: template contract export, authoring-to-runtime compilation, shaping, generation orchestration, and `.pptx` writing.
- `autoreport/web/app.py`: user-facing web app for the streamlined AI-draft-to-PPTX flow.
- `autoreport/web/debug_app.py`: developer-facing debug app for contract, normalization, compiled payload, and upload inspection.
- `tests/`: executable contract for CLI, schema, PowerPoint, and web behavior.

## Verification Defaults
- Use the repository virtualenv by default: `.\venv\Scripts\python.exe`
- CLI or entrypoint changes: `.\venv\Scripts\python.exe -m unittest tests.test_cli`
- Loader or schema changes: `.\venv\Scripts\python.exe -m unittest tests.test_loader tests.test_validator`
- Generation or writer changes: `.\venv\Scripts\python.exe -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`
- User web app changes: `.\venv\Scripts\python.exe -m unittest tests.test_web_app`
- Debug web app changes: `.\venv\Scripts\python.exe -m unittest tests.test_web_debug_app`
- Cross-cutting changes: run the narrow focused tests first, then expand to the relevant combination above.

## Generated Artifacts
- Do not commit generated output from `output/`.
- Keep temporary test artifacts under `tests/_tmp/`.
- Keep versioned post Markdown source under `docs/posts/*.md` tracked so guide, release-note, and devlog changes stay reviewable with the code they describe.
- Keep reusable static public-doc assets under `docs/shared-assets/` when they should persist across releases.
- Keep versioned screenshot capture folders under `docs/posts/*-image-v*/` local-only unless the asset is intentionally promoted into a tracked shared path.
- Keep local bootstrap state under `.codex/`; repo-tracked shared guidance belongs in `codex/`.

## Branch Roles
- `main`: released stable line and source of truth for release tags.
- `codex/next`: curated release-candidate line for the next version. Keep it intentionally reviewable rather than using it as the scratch feature branch or a routine direct-commit work branch. Reserve direct commits there for intentional integration work such as promotion, merge, squash, sync, or release cleanup.
- `codex/master`: protected integration branch when present. Do not treat it as a routine direct-commit work branch. Reserve direct commits there for intentional integration work such as merge, sync, or other branch-maintenance tasks unless the user explicitly overrides that rule.
- `codex/v<next>-master`: active development line for the next planned version when the user wants branch-based feature work before release promotion. Direct commits remain allowed there under the current repo policy.

## Skill Routing
- Load `codex/skills/autoreport-dev/SKILL.md` first for repository context.
- Then load one primary focused skill based on the main surface being changed:
- CLI, argparse, exit codes, user-visible command output -> `autoreport-cli`
- YAML loading, models, validator rules, template/report payload examples, schema tests -> `report-schema`
- Template shaping, generation orchestration, writer behavior, template compatibility -> `pptx-output`
- Active `codex/v0.3-*` task worktree monitoring, master-thread orchestration, and `.codex/master-next.txt` dispatch -> `workstream-orchestrator`
- FastAPI user app, debug app, shared web API routes, HTML surfaces, API error shape, web tests -> `web-demo`
- Branch choice, protected integration branches, and commit/push guards for `codex/next` or `codex/master` -> `branch-commit-guard`
- Shared repo-operation surfaces such as `AGENTS.md`, `codex/skills/`, tracked deployment handover docs, and shared architecture/process guidance -> `repo-ops-policy-sync`
- Remote EC2/public app handover, deployment drift checks, systemd/nginx or container refresh, and public-vs-debug entrypoint confirmation -> `remote-deployment-handover`
- Public repo safety, secrets/PII leak checks, screenshot hygiene, and preflight before any public push/publish -> `public-repo-safety`
- Release readiness checks, browser smoke tests, screenshots, download evidence, and verification-backed doc inputs -> `release-verification`
- README, release notes, packaging metadata, public wording alignment -> `release-docs`
- Release backup tags, squashed promotion from `codex/v<next>-master` into `codex/next`, merged-source-branch cleanup, and refreshing `codex/next` from `main` after release -> `release-tagging`
- WordPress-style public Markdown posts for development logs, release notes, and user guides -> `write-doc-markdown`
- Versioned post handoff from `docs/posts/` into the private `autorelease` publishing repo -> `autorelease-handoff`
- If a task genuinely spans multiple surfaces, keep one primary skill and consult adjacent skills only where necessary.

## Bootstrap Rules
- When both repo-local and personal/global skills exist, explicitly load the repo-local path under `codex/skills/` and treat it as authoritative for this repository.
- If a focused skill is missing or incomplete, continue with this baseline plus `autoreport-dev` and report the coverage gap instead of hard-failing the session.
- Keep AI/process guidance out of the public product story; do not move bootstrap narrative into `README.md` unless there is an explicit contributor-facing reason.
- Treat stale code, stale sample payloads, stale UI copy, and other superseded implementation paths as blockers rather than optional cleanup.
- When a task replaces a public contract, homepage flow, CLI path, or template behavior, remove the superseded tracked code, docs, tests, and examples in the same task unless compatibility is intentionally preserved.
- Do not keep "old but maybe useful later" tracked code as a safety blanket; rely on git history, tags, and explicit compatibility shims instead of leaving dead paths in the live repo.
- If compatibility really must remain, document that choice and keep it covered by tests so it is an explicit supported path rather than leftover code trash.
- Treat `AGENTS.md` and the repo-local skills under `codex/skills/` as part of the live operating surface, not as optional side documentation.
- When shipped behavior, public contracts, cleanup rules, verification flow, or orchestration expectations change, update the relevant repo-local skills and bootstrap guidance in the same task so future turns inherit the latest repo reality.
- Stale agent or skill guidance is a blocker for signoff for the same reason stale code is a blocker: it causes later tasks to resurrect dead paths and wrong assumptions.
- Use git history and tags for recovery, not stale bootstrap guidance left in tracked files after the product has already moved on.
- Before staging, committing, or pushing from `codex/next` or `codex/master`, load `codex/skills/branch-commit-guard/SKILL.md` and stop unless the work is intentional protected-branch integration work such as promotion, merge, squash, sync, or release cleanup, or the user explicitly authorizes another direct commit on that branch.
- Treat `codex/next` and `codex/master` as protected integration branches for Codex-authored work. Use child branches for routine changes instead of incremental direct commits there, and keep direct commits on the protected branches for deliberate integration history only.
- When the user prefers the version-master branch flow, do active feature work on `codex/v<next>-master`, then squash or otherwise intentionally condense that history into `codex/next` before release prep.
- In that flow, keep `main` release-oriented rather than treating it as the scratch feature branch.
- Prefer bumping `pyproject.toml` and package version markers when the curated release candidate lands on `codex/next`, not at the start of `codex/v<next>-master`, unless the user explicitly wants the early bump.
- Create annotated release tags only on the merged `main` commit after `codex/next` has been promoted into `main`.
- After tagging, refresh `codex/next` from the tagged `main` commit before starting the next version-master line unless the user explicitly wants a different branch shape.
- Treat repo-operation tasks on `AGENTS.md`, `codex/skills/`, tracked deployment handover docs, and shared architecture/process guidance as operational changes rather than draft-only docs work.
- Unless the user explicitly asks to stop earlier or use a different branch flow, finish those repo-operation tasks by validating the changed guidance, running `public-repo-safety`, committing on `main`, pushing `origin/main`, and refreshing `codex/next` from that pushed `main`.
- When public release-site URLs or hosted demo endpoints change, update `docs/deployment/public-service-info.yaml` in the same task and keep the writing/handoff skills aligned so the homepage, guide, and release-facing posts do not drift.
- Keep the user-facing web app and the developer-facing debug app as separate tracked surfaces.
- The user app should stay optimized for the single "copy AI package -> paste draft -> generate" flow.
- If a task needs extra panes, inspection widgets, manual helpers, or internal compile/normalize visibility, add or refine them in the debug app before cluttering the user app.
- Shared compile/generate route behavior may be reused between the two apps, but the debug app must not become a hidden second implementation of the generation pipeline.
- Treat the debug app primarily as a developer-facing validation workbench for contract inspection, normalization/compiled-payload analysis, upload debugging, and selected-case reruns.
- If future work adds robustness checks across large prompt corpora or many template permutations, keep the high-volume execution in CLI or batch runners and let the debug app inspect summaries, failures, and representative reruns instead of becoming the bulk execution engine.
- For tracked policy changes under `AGENTS.md`, `codex/skills/`, or shared architecture docs, do not treat the change as complete until it is committed on `main`, pushed, and `codex/next` has been refreshed from that pushed `main` when `next` is part of the active branch flow.
- When old sibling directories from retired `codex/v0.3-*` worktrees remain under the workspace root, clean them through the tracked workstream-orchestrator cleanup flow instead of leaving manual filesystem cleanup to the user.
- If retired worktree cleanup is blocked by a Windows directory lock on an otherwise empty `autoreport_v0.3-*` sibling, ask the user to restart the Codex desktop app first and then rerun the tracked cleanup flow before escalating to stronger manual cleanup steps.
- For master-thread orchestration, once branch-specific instructions have been written into each active worktree's `.codex/master-next.txt`, treat that file as the only authoritative branch-specific instruction channel.
- After `.codex/master-next.txt` has been written, do not restate branch-specific tasks, owned-file lists, or per-branch test commands in user-facing chat unless the user explicitly asks for the branch details or a worktree is missing its instruction file.
- The normal user-facing follow-up after instruction dispatch is one shared broadcast telling workers to reload the latest policy/skill files and then follow their local `.codex/master-next.txt`.
- When a new master-thread starts and valid `.codex/master-next.txt` files already exist, continue from that shared-broadcast pattern instead of generating a fresh branch-by-branch handoff in chat.
- For workstream report-channel files under `.codex/worker-status.json` and `.codex/worker-final.json`, do not invent ad-hoc JSON shapes. Use the canonical report contract from `codex/skills/workstream-orchestrator/references/orchestration.md` and the example JSON templates under that same reference folder.
- Before a worker claims `ready_for_review` or writes `.codex/worker-final.json`, rerun the collector against that workstream and treat report-contract errors as blockers rather than optional cleanup.
- Before any public push, PR, release, publish-ready doc handoff, or claim that the repo is safe to share publicly, load `codex/skills/public-repo-safety/SKILL.md` and run its blocker checks.
- If `public-repo-safety` finds a blocker in a tracked file or a non-ignored untracked file, stop the public-sharing flow until the finding is removed or intentionally resolved.
- Do not promote ignored screenshots or local artifacts into tracked docs paths without reviewing them through `public-repo-safety`.
- When a release backup tag is created in this repository, prefer an annotated `v<version>` tag on the merged `main` release commit, then delete the merged source branch and refresh `codex/next` from the updated `main` unless the user explicitly asks for a different branch flow.
- If a task ends a branch, prepares a tag, or wraps up versioned public posts under `docs/posts/`, run `codex/skills/autorelease-handoff/SKILL.md` unless the user explicitly opts out of the private publishing handoff.
