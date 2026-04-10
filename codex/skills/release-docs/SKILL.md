---
name: release-docs
description: Keep README, package metadata, examples, and repo-tracked public wording aligned with the current autoreport implementation. For WordPress-style development logs, release notes, and user guides, use the dedicated `write-doc-markdown` skill.
---

# Release Docs

## Overview

Use this skill for `README.md`, `pyproject.toml`, release notes,
example payload wording, packaging text, and other public-facing project descriptions
that live in the repository. Use `write-doc-markdown` for WordPress-style post generation.
If the task is really about `AGENTS.md`, `codex/skills/`, tracked deployment
handover notes, or other shared repo-operation guidance, switch to
`repo-ops-policy-sync` instead of treating it as ordinary release wording.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/public-surfaces.md`.
- Read `../../../README.md`.
- Read `../../../pyproject.toml`.
- Read any relevant repo-tracked `release-note-*.md` files when version framing or historical messaging matters.
- Read `../../../examples/autoreport_editorial_template_contract.yaml`.
- Read `../../../examples/autoreport_editorial_report_payload.yaml`.
- Read `../../../examples/report_payload.yaml`.
- Read `../../../examples/report_payload.json`.
- Read `../public-repo-safety/SKILL.md` before final public signoff or before promoting screenshots into tracked docs.
- If the task also creates a release backup tag or refreshes release branches after merge, consult `../release-tagging/SKILL.md`.
- If the user wants a WordPress-style post, switch to `../write-doc-markdown/SKILL.md`.
- If the task should sync versioned posts into the private publishing repo, also consult `../autorelease-handoff/SKILL.md`.
- If the user wants the docs backed by fresh smoke-test evidence, browser captures, or release signoff notes, also consult `../release-verification/SKILL.md`.
- If docs describe a runtime behavior, inspect the matching code/tests before editing.

## Workflow

1. Prefer implemented truth over aspirational text.
- Keep README and metadata aligned with what the code and tests do today.
- When roadmap text is needed, label it clearly as future work.

2. Keep public messaging product-first.
- Do not move bootstrap or AI-process narrative into top-level product copy by default.
- Keep contributor/bootstrap guidance in `AGENTS.md` and repo-local skills instead.
- Treat WordPress-style blog posts as a separate writing surface owned by `write-doc-markdown`.

3. Update linked surfaces together.
- If entrypoints change, update README and `pyproject.toml` together.
- If the example payload changes, keep it aligned with validator behavior.
- If version framing changes, audit release notes and public wording for stale references.

4. Treat mismatches as intentional work, not incidental cleanup.
- If you discover docs/code drift, either fix it in the same change or call it out explicitly.

## Current Constraints

- README should describe the contract-first Autoreport flow with CLI and web-demo entry points.
- Package name, version, and entrypoint metadata should be taken from `pyproject.toml`, not copied into skill docs as fixed values.
- Public examples should point to the current contract/payload files, not the retired weekly-only example.
- Legacy weekly-report terminology may still appear in internal module names or historical docs; do not present it as the current public contract.

## Output Contract

- State which public-facing surface was updated.
- Cite code/tests when tightening or correcting behavior claims.
