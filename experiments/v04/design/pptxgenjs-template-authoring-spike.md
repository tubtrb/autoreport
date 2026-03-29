# v0.4 PptxGenJS Template-Authoring Spike

## Goal

This spike tests whether `PptxGenJS` is practical as a branch-local template
authoring tool for `autoreport`.

The goal is not to replace the current Python runtime.
The goal is to see whether `PptxGenJS` can generate PowerPoint-native
placeholder templates that the current v0.4 worktree can already inspect and
fill through the existing Python interfaces.

This remains an internal authoring question, not a product-direction question.
Autoreport's product runtime still centers on analyzing user-provided or
already-existing templates rather than making template creation itself the main
feature.

## Boundaries

- `PptxGenJS` is used only as a template authoring tool in `codex/v0.4-incubator2`
- `python-pptx` and the current Python generation runtime remain unchanged
- no CLI, web, or public product surface is modified
- no root `package.json` is introduced
- the spike may help build first-party seed templates, but it does not redefine
  the product around template creation

## Why the Node workspace is prototype-local

The spike adds Node tooling only under
`experiments/v04/prototypes/pptxgenjs_template_spike/` so it stays removable and
does not change the repository root contract.

That keeps the experiment honest:

- the runtime continues to depend on Python only
- the Node dependency is scoped to authoring evidence
- the branch can decide later whether any part of this should graduate

## Why the matrix starts with three templates

Three fixtures are enough to test the main authoring questions without turning
the spike into an open-ended design exercise.

- `v04-minimal-text-template.pptx`
  - title + subtitle
  - title + single body placeholder
  - baseline text-only compatibility
- `v04-stacked-text-template.pptx`
  - title + subtitle
  - title + two vertically stacked body placeholders
  - multi-slot and `stack` orientation compatibility
- `v04-text-image-template.pptx`
  - title + subtitle
  - title + body + picture + caption placeholder
  - image-capable slot detection and caption pairing compatibility

## Success question

This spike is successful only if the current Python interfaces can inspect and
fill these authored templates without runtime changes.

If inspection or generation fails, the evidence still has value as long as the
failure is reproducible and the placeholder structure is documented clearly
enough to support a verdict.

## Current scoped outcome

The current intended graduation path is:

- keep `PptxGenJS` as an internal template authoring lane
- use it to create Autoreport-owned text-first templates and safe fixtures
- keep runtime inspection, payload validation, and deck generation in Python

Any broader move, such as runtime replacement or Node-owned contract export,
would require a separate decision with stronger evidence than this spike
currently provides.
