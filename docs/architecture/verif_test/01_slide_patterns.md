# Manual AI Regression Slide Patterns

This folder is the canonical verification runbook for the public manual AI flow.
The tracked case source of truth is [`tests/verif_test/cases/manual_public_cases.yaml`](../../../tests/verif_test/cases/manual_public_cases.yaml).

## Fixed Suites

| Suite | Cases | Intent |
| --- | --- | --- |
| `smoke` | `01_one_image_canary`, `01_two_image_canary`, `01_three_image_canary` | Fast transport, checker, and PPTX proof across 1, 2, and 3 image slides |
| `regression` | `smoke` + `05_balanced_canary`, `05_dense_text_canary` | Add realistic mixed-body decks and denser manual text |
| `full` | `regression` + `10_full_family_canary` | Canonical wide run that covers the full public one-image family plus longer output review |

## Case Contract

Every case is defined by these fixed fields:

- `body_slide_count`
- `pattern_order`
- `text_density`
- `image_ref_count`
- `expected_review_required`

The current representative cases are fixed:

- `01_one_image_canary`
- `05_balanced_canary`
- `10_full_family_canary`

## Pattern Coverage

The full canonical suite union must cover:

- `text.manual.section_break`
- all public one-image manual presets
- `text_image.manual.procedure.two`
- `text_image.manual.procedure.three`

The current coverage split is intentional:

- `smoke` proves the minimal 1/2/3-image paths
- `regression` adds section-break and denser prose behavior
- `full` adds the broad one-image family sweep used for representative visual review

## Notes

- `body_slide_count` counts body slides only, not `title_slide` or `contents_slide`.
- Public manual verification stays scoped to the built-in `autoreport_manual` flow in v1.
- If a new public manual pattern is added, update the case catalog in the same change.
