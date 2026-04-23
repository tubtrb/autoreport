---
content_type: page
title: Manual Draft Workflow
slug: manual-draft-workflow
summary: "How to move from the built-in starter to a checked draft and a final PowerPoint download."
date: 2026-04-11
status: publish
source_repo: tubtrb/autoreport
source_ref: v0.4.2
---

# Manual Draft Workflow

The current hosted flow is built around a guided manual starter. The goal is not to hide the process. The goal is to keep each step visible enough that a user can correct the draft before generation.

## Recommended sequence

1. Open the hosted demo.
2. Keep the built-in starter in the editor.
3. Copy the brief into another AI or edit the YAML directly.
4. Paste the filled draft back into the editor.
5. Run `Check Draft`.
6. Run `Refresh Preview`.
7. Attach screenshots only where the preview rail asks for them.
8. Generate the final `.pptx`.

## Why the sequence matters

This order avoids two common mistakes:

- generating before the YAML shape is checked
- uploading screenshots before the preview rail reflects the current draft

If you follow the steps in order, the public workflow stays easier to understand and easier to recover when something is slightly off.

## Common mistakes

- replacing the root structure instead of filling the expected draft
- skipping `Check Draft` after a large edit
- forgetting to refresh the preview after changing slide structure
- uploading an image to the wrong preview row

## Expected outcome

When the flow is followed cleanly, the browser should download `autoreport_demo.pptx` after generation succeeds.
