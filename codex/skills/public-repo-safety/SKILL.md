---
name: public-repo-safety
description: Check the autoreport repository for public-release safety issues such as secrets, personal identifiers, local absolute paths, unsafe screenshots, and accidental artifact promotion. Use when Codex is preparing a public commit, push, release, PR, publish-ready doc set, or any other output that could leave the local machine or become visible outside the private workspace.
---

# Public Repo Safety

## Overview

Use this skill to run a public-facing safety pass before anything in this
repository is treated as publishable. The goal is to catch leaks early and
block public signoff when repo-bound files still contain secrets, personal data,
internal-only screenshots, or other accidental disclosures.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../.gitignore`.
- Read `references/public-preflight.md`.
- Read `references/screenshot-hygiene.md` when images, docs, or browser artifacts are involved.
- If the task is about release readiness, also read `../release-verification/SKILL.md`.
- If the task is about README, release notes, or other public text, also read `../release-docs/SKILL.md`.
- If the task is about WordPress-style docs or draft content handoff, also read `../write-doc-markdown/SKILL.md`.

## Workflow

1. Scope only what could enter the public repo.
- Check tracked files first.
- Check untracked files that are not ignored and could plausibly be added next.
- Treat ignored files as local-only unless the user explicitly plans to promote them.

2. Scan for high-risk leak categories.
- Secrets and credentials: API keys, access tokens, private keys, passwords, application passwords.
- Personal identifiers: real names, usernames, email addresses, phone numbers, local account names.
- Local machine traces: absolute paths such as `<workspace>/...` or `/home/<user>/...`.
- Unsafe screenshots: OS-level captures that show personal accounts, local folders, chat windows, internal tools, or unrelated app content.
- Internal-only process details that should not land in public product-facing docs.

3. Distinguish blocker findings from local-only noise.
- A finding in a tracked file is a blocker for public release.
- A finding in a non-ignored untracked file that could be added is also a blocker until resolved.
- A finding only inside ignored local artifacts is not a public-repo blocker, but should still be called out if the user might later reuse that artifact.

4. Enforce a stop rule.
- If a blocker finding exists, do not recommend pushing, publishing, tagging, or calling the repo public-ready.
- Ask for cleanup or removal instead of treating it as optional polish.
- Do not rely on "probably ignored" or "not intended for commit" when the file is still repo-bound.

5. Hand off a publish-safe result.
- When no blocker findings remain, say that the repo-bound set appears safe based on the scan scope used.
- If there are residual local-only risks, name them separately so they are not confused with public repo risk.

## Current Repo Defaults

- `output/`, `.playwright-cli/`, `docs/posts/`, and `.codex/` are ignored by default in this repo.
- Ignored browser artifacts can still contain unsafe captures, so review them before promoting any image into a tracked location.
- Browser-generated full-page captures are usually safer for public docs than OS-level active-window screenshots.

## Severity Rules

- `P0`: direct secret or credential in a repo-bound file.
- `P1`: personal identifier, local absolute path, or unsafe screenshot in a repo-bound file.
- `P2`: sensitive content only in ignored local artifacts, or weaker hygiene issues that are worth cleaning before reuse.

## Output Contract

- State the scan scope: tracked only, tracked plus candidate untracked, or also ignored artifacts.
- List blocker findings first with concrete file references.
- State clearly whether the repo is blocked or clear for public release.
- If blocked, do not soften the result into a suggestion; say that public release should stop until the finding is removed.
