---
content_type: page
title: Draft Checker and Repair
slug: draft-checker-and-repair
summary: "What Draft Checker validates, what repair can fix, and what still needs manual correction."
date: 2026-04-11
status: publish
source_repo: tubtrb/autoreport
source_ref: v0.4.2
---

# Draft Checker and Repair

`Draft Checker` exists to catch structure problems before generation. In `v0.4.2`, it also helps recover one of the most common failure cases in AI-assisted YAML authoring: indentation drift.

## What Draft Checker does

- checks that the draft still follows the supported structure
- surfaces warnings before generation
- returns repaired YAML to the editor when a supported repair succeeds

## What the repair path can help with

The repair logic is intentionally narrow. It is meant for common indentation collapse, not for every form of broken input.

This matters because a repair feature is only helpful when the user can still understand what came back. A narrow repair path is easier to trust than a loose auto-fix that silently changes too much.

## What still needs manual correction

Some drafts still require the user to edit the YAML directly:

- the wrong root structure
- unsupported pattern names
- missing required manual sections
- prose that is not YAML at all

## Practical advice

Use `Draft Checker` after every meaningful draft change, especially when the text came from another AI. It is the fastest way to catch a structure problem before preview and generation drift apart.
