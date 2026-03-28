# Public Preflight

## Purpose

Use this checklist before any public push, PR, release, or public-facing handoff.

## Scope Order

1. Tracked files
2. Non-ignored untracked files
3. Ignored artifacts only when they may be promoted later

## Blocker Categories

- secrets or credentials
- personal names, usernames, emails, phone numbers
- local absolute filesystem paths
- screenshots containing unrelated windows or personal account details
- public docs that accidentally describe internal-only process or hidden tooling as product behavior

## Minimal Command Shape

Use the repo-bound file set first:

- `git grep` for tracked files
- `git ls-files --others --exclude-standard` for non-ignored untracked files
- `git check-ignore` when you need to prove whether an artifact is currently protected by `.gitignore`

Prefer scanning the candidate file set rather than the whole working directory so `venv/` and other local noise do not drown out the real public risk.

## Stop Rule

If any blocker category is found in a tracked file or a non-ignored untracked file, stop the public-release flow and report the exact path.
