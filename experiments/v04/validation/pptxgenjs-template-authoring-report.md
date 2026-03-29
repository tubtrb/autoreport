# PptxGenJS Template-Authoring Spike Report

## Scope

- Spike type: template authoring only
- Runtime replacement: no
- Python runtime changes: none
- Working root: `codex/v0.4-incubator2`
- Evidence file: `experiments/v04/validation/pptxgenjs-template-authoring-evidence.json`

## Environment

- Node: `v24.13.1`
- npm: `11.8.0`
- Python: `3.14.3`

## Template Outputs
- `experiments/v04/prototypes/pptxgenjs_template_spike/generated/v04-minimal-text-template.pptx`
- `experiments/v04/prototypes/pptxgenjs_template_spike/generated/v04-stacked-text-template.pptx`
- `experiments/v04/prototypes/pptxgenjs_template_spike/generated/v04-text-image-template.pptx`

## Results

### `v04-minimal-text-template.pptx`

- Inspection: success
- Contract extraction: success
- Generation smoke: success
- `template_id`: `template-bb7997259d91`
- Contract summary:
  - title_slide: text=2 image=0
  - contents_slide: text=2 image=0
  - text: text=2 image=0
  - metrics: text=2 image=0
- Generated deck reopened with visible titles:
  - `Autoreport`
  - `Contents`
  - `What It Does`
  - `Adoption Snapshot`

### `v04-stacked-text-template.pptx`

- Inspection: success
- Contract extraction: success
- Generation smoke: success
- `template_id`: `template-3e438d2b51af`
- Contract summary:
  - title_slide: text=2 image=0
  - contents_slide: text=3 image=0
  - text: text=3 image=0
  - metrics: text=3 image=0
- Generated deck reopened with visible titles:
  - `Autoreport`
  - `Contents`
  - `What It Does`
  - `Adoption Snapshot`

### `v04-text-image-template.pptx`

- Inspection: success
- Contract extraction: success
- Generation smoke: success
- `template_id`: `template-daf4cf044239`
- Contract summary:
  - title_slide: text=2 image=0
  - contents_slide: text=2 image=0
  - text: text=2 image=0
  - metrics: text=2 image=0
  - text_image: text=3 image=1
- Generated deck reopened with visible titles:
  - `Autoreport`
  - `Contents`
  - `What It Does`
  - `Adoption Snapshot`
  - `Why It Matters`

## Final Verdict

`viable`

## Why

- All three fixtures inspect and generate cleanly, including the mixed text-image template.
