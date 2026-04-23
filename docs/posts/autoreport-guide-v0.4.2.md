# User Guide

Version: `v0.4.2`
Release date: `2026-04-11`
Status: `draft`

This guide is for the hosted Autoreport demo. It covers the current public browser flow: start from the built-in manual starter, edit the YAML or paste a filled draft from another AI, use `Slide Style Gallery` to add or remove supported slides, run `Check Draft`, use `Refresh Preview`, attach screenshots only where the current draft needs them, and download the generated PowerPoint deck.

For version-specific changes, see the release notes.

## Open the hosted demo now

If you want to use Autoreport immediately, start here:

- [Open the hosted Autoreport demo](http://3.36.96.47/)
- [Open the Updates page](http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/)
- [Back to the overview](http://auto-report.org/)

## Hosted demo flow

1. Open the hosted demo and keep the built-in manual starter in the editor.
2. Edit the starter YAML directly, or copy the brief into another AI and paste the returned YAML back into the editor.
3. Use the `Slide Style Gallery` and `Add Slide` to append another supported manual slide layout when you need more structure.
4. Use `Delete` on the right preview rail when you want to remove the contents slide or a manual content slide from the current draft.
5. Run `Check Draft` and review any warnings before generation.
6. Select `Refresh Preview` so the right rail matches the current YAML.
7. If the current draft needs images, attach screenshots only in the listed upload panels beside the matching slide previews.
8. Select `Generate PPTX` and wait for the browser download.

### 1. Send the starter brief to another AI

The starter YAML already includes the brief that explains the expected response shape. Copy that brief into another AI and ask it to return only the filled manual draft.

![Gemini starter brief](../shared-assets/user-guide-ai-insert/gemini-insert.png)

![ChatGPT starter brief](../shared-assets/user-guide-ai-insert/chatgpt-insert.png)

### 2. Add or remove supported slides before you generate

The public demo is not limited to only the original starter sequence. You can use the `Slide Style Gallery` to filter supported manual layouts, choose a preset card, and select `Add Slide` to append it to the current draft. When a contents slide or manual content slide is no longer needed, use `Delete` from the right preview rail to remove it from the current draft.

![Starter editor and slide gallery](guide-image-v0.4.2/01-manual-starter-loaded.png)

### 3. Check the YAML and refresh the preview rail

`Check Draft` verifies the built-in manual structure before generation. In `v0.4.2`, the checker can also recover common indentation drift and return the repaired YAML to the editor with a warning so the flow does not fail immediately for a minor formatting collapse.

After you change the YAML, select `Refresh Preview`. The right rail updates to show the current slide order, the current upload panels, and the slides that can be deleted from the draft.

![Preview rail refreshed](guide-image-v0.4.2/02-refresh-slide-assets-complete.png)

### 4. Add screenshots only when the current draft needs them

If the current draft includes image-bearing slides, the right rail shows one upload panel beside each matching preview row. Paste or choose one screenshot per row and keep each screenshot aligned with the preview it belongs to.

![Aligned screenshot upload panel](guide-image-v0.4.2/03-upload-row-filled.png)

### 5. Generate and download

When the draft looks correct and the required screenshots are attached, select `Generate PPTX`. The browser download starts after the hosted demo reports success.

![Generation success](guide-image-v0.4.2/05-generate-success.png)

## Expected result

- The draft stays centered on the built-in manual starter flow, even after you add or remove supported slides
- The checker can return corrected YAML to the editor when it repairs common indentation drift
- The preview rail stays aligned with the current YAML after `Refresh Preview`
- The browser download starts as `autoreport_demo.pptx`

## Browser check

The local `v0.4.2` public web flow was rechecked in Playwright on `2026-04-11`, including the starter load, preview refresh, aligned upload panel, and generation-success states.
