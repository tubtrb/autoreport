## Autoreport v0.4.2 Release Notes

Version: `v0.4.2`
Release date: `2026-04-11`
Status: `draft`

Autoreport `v0.4.2` is a stabilization release for the hosted manual flow, not a broader product-scope expansion. The release keeps the same built-in manual starter path, but tightens the AI starter brief, reduces one of the main failure points in that flow, and keeps the preview rail and upload panels aligned with the YAML the user is actually editing.

## Live service

As of `2026-04-11`, the public site and hosted demo are available at:

- Home: `http://auto-report.org/`
- Guide: `http://auto-report.org/guide/`
- Updates: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo: `http://3.36.96.47/`

## What's included in this release

- The built-in manual starter now gives stricter guidance about the expected `report_content` response shape
- `Check Draft` can recover common manual YAML indentation drift before it rejects an otherwise usable draft
- When a repair is applied, the corrected YAML is returned to the editor together with a warning so the user can review it before generation
- `Refresh Preview` re-syncs the preview rail and screenshot upload panels with the current YAML
- The public flow supports lightweight manual slide changes through `Slide Style Gallery`, `Add Slide`, and `Delete`
- Screenshot upload remains aligned to the matching preview row
- The browser download remains `autoreport_demo.pptx`

## Basic usage

1. Open the hosted demo and keep the built-in manual starter in the editor.
2. Copy the starter brief into another AI and ask it to fill the draft.
3. Paste the returned YAML back into the editor.
4. Use `Slide Style Gallery` and `Add Slide` when you need another supported manual slide, or `Delete` when you want to remove a contents slide or manual content slide.
5. Run `Check Draft` and review any warnings before generation.
6. Select `Refresh Preview` so the preview rail and upload panels match the current YAML.
7. If the current slides require screenshots, attach each image beside the matching preview row.
8. Select `Generate PPTX` and download the deck.

## Supported draft shape

- Return a single YAML response rooted at `report_content`
- Keep the manual title slide and contents slide structure from the starter
- Use the supported manual slide patterns from the built-in brief instead of inventing new pattern names
- Keep the slide list in the same order you want the generated deck to follow

## Error handling

- The checker still blocks unsupported structure, missing required manual sections, and clearly invalid pattern choices
- The new repair path is focused on common indentation drift rather than arbitrary YAML corruption
- Warnings are meant to keep the user in the flow while still exposing what was corrected

## Browser check

- The hosted demo health endpoint returned `{"status":"ok"}` on `2026-04-11`
- The public hosted demo homepage responded with the built-in manual starter signals on `2026-04-11`

## Current limitations

- The repair path is targeted at common manual YAML indentation drift only
- Drafts that use the wrong root, unsupported pattern names, or non-YAML prose still need manual correction
- Mobile or phone support is not separately confirmed in the scope of this release
- The public site narrative may still reflect `v0.4.1` until the `v0.4.2` candidate handoff is published; these notes should be treated as candidate-facing release copy rather than proof that the public site is already refreshed
- The public hosted demo remains focused on the built-in manual starter rather than a broader custom authoring flow

## Next steps

- Keep tightening the manual starter wording so external AIs return the supported structure more consistently
- Continue validating the same hosted flow against larger saved corpora before widening the public authoring surface
