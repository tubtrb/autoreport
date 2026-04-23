# Manual AI Regression Prompt And YAML Generation

## Source Of Truth

- Case definitions: [`tests/verif_test/cases/manual_public_cases.yaml`](../../../tests/verif_test/cases/manual_public_cases.yaml)
- Builder logic: [`tests/verif_test/catalog.py`](../../../tests/verif_test/catalog.py)
- Public manual prompt header: [`autoreport/web/app.py`](../../../autoreport/web/app.py)

## Generation Rules

Each prepared case emits:

- `starter.yaml`
- `prompt.txt`
- `case-manifest.json`

`prompt.txt` is generated from:

1. the current public manual instruction header from `autoreport/web/app.py`
2. the case-specific `starter.yaml` built from the tracked case catalog

The generation rules stay fixed:

- always keep the full public manual YAML-only completion block
- always include one complete `report_content` YAML document
- only vary case-specific content:
  - slide titles
  - pattern order
  - text density
  - image refs
  - captions

The prompt header is intentionally canonical across the public app and verification
runner:

- return YAML only
- start with `report_content:`
- copy the starter structure exactly and edit only slot values
- keep the starter body slide count, pattern order, and image refs

## Starter YAML Shape

Every generated starter keeps:

- `title_slide.pattern_id = cover.manual`
- `contents_slide.pattern_id = contents.manual`
- body slides limited to the supported public manual pattern set

The builder assigns:

- dotted step numbering such as `1.1`, `1.2`
- sequential upload refs such as `image_1`, `image_2`
- density-specific `detail_body` text

## Prompt Pack Export

Compatibility prompt packs are exported from the same case catalog through:

[`codex/skills/ai-corpus-verification/scripts/export_product_prompt_pack.py`](../../../codex/skills/ai-corpus-verification/scripts/export_product_prompt_pack.py)

That export is a compatibility layer. The canonical tracked source remains the case catalog.
