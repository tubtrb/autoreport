---
name: release-docs
description: Keep README, release notes, package metadata, examples, and public wording aligned with the current autoreport implementation.
---

# Release Docs

## Overview

Use this skill for `README.md`, `pyproject.toml`, release notes,
example payload wording, packaging text, and other public-facing project descriptions.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/public-surfaces.md`.
- Read `../../../README.md`.
- Read `../../../pyproject.toml`.
- Read any relevant repo-tracked `release-note-*.md` files when version framing or historical messaging matters.
- Read `../../../examples/weekly_report.yaml`.
- If docs describe a runtime behavior, inspect the matching code/tests before editing.

## Workflow

1. Prefer implemented truth over aspirational text.
- Keep README and metadata aligned with what the code and tests do today.
- When roadmap text is needed, label it clearly as future work.

2. Keep public messaging product-first.
- Do not move bootstrap or AI-process narrative into top-level product copy by default.
- Keep contributor/bootstrap guidance in `AGENTS.md` and repo-local skills instead.

3. Update linked surfaces together.
- If entrypoints change, update README and `pyproject.toml` together.
- If the example payload changes, keep it aligned with validator behavior.
- If version framing changes, audit release notes and public wording for stale references.

4. Treat mismatches as intentional work, not incidental cleanup.
- If you discover docs/code drift, either fix it in the same change or call it out explicitly.

## Current Constraints

- README currently describes a deterministic weekly report pipeline with CLI and web-demo entry points.
- Package name, version, and entrypoint metadata should be taken from `pyproject.toml`, not copied into skill docs as fixed values.
- The example YAML file still carries a `v0.1` comment at the top.
- Some validator strings still mention `v0.1`; changing them is a contract change, not just copy editing.

## Output Contract

- State which public-facing surface was updated.
- Cite code/tests when tightening or correcting behavior claims.
