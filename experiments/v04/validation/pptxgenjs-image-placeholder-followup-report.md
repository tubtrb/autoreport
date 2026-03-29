# v0.4 PptxGenJS Image Placeholder Follow-up Report

## Summary

- Goal: reassess the mixed image/text placeholder comparison after rebasing onto the latest `v0.3-master` runtime and applying the incubator hardening patches.
- Final verdict: `runtime_hardened`
- Scope: branch-local diagnostics only under `experiments/v04/`

## Environment

- Node: `v24.13.1`
- npm: `11.8.0`
- Python: `3.14.3`

## Commands

- `npm ci`
- `node generate_templates.mjs`
- `.\.venv\Scripts\python.exe experiments/v04/prototypes/pptxgenjs_template_spike/image_placeholder_followup.py --write-validation --pretty`
- `.\.venv\Scripts\python.exe -m unittest tests.test_pptxgenjs_template_spike tests.test_pptxgenjs_image_placeholder_followup`
- `.\.venv\Scripts\python.exe -m unittest tests.test_workflow_automation_spike tests.test_v04_prototype_scaffolds tests.test_workflow_automation_sandbox`
- `.\.venv\Scripts\python.exe -m unittest tests.test_generator`

## Deck Matrix

- `baseline`
  path: `experiments\v04\prototypes\pptxgenjs_template_spike\generated\v04-text-image-template.pptx`
  body layout: `V04 Text Image Body`
  body text slots: `101:body:stack`
  body image slots: `102:object:stack`
  text written into image placeholder: `no`
- `pic_token`
  path: `experiments\v04\prototypes\pptxgenjs_template_spike\generated\v04-text-image-pic-token-template.pptx`
  body layout: `V04 Text Image Pic Token Body`
  body text slots: `101:body:stack`
  body image slots: `102:object:stack`
  text written into image placeholder: `no`
- `compact_image`
  path: `experiments\v04\prototypes\pptxgenjs_template_spike\generated\v04-text-image-compact-image-template.pptx`
  body layout: `V04 Text Image Compact Body`
  body text slots: `101:body:stack`
  body image slots: `102:object:stack`
  text written into image placeholder: `no`
- `control`
  path: `experiments\v04\prototypes\pptxgenjs_template_spike\generated\v04-control-text-picture-template.pptx`
  body layout: `V04 Control Mixed Body`
  body text slots: `1:body:stack`
  body image slots: `4:picture:stack`
  text written into image placeholder: `no`

## Verdict Reasons

- all four comparison decks now inspect into a reusable `text_image` pattern under the rebased runtime
- actual profiled image placeholder indices remain separate from body and caption indices, and the generated decks no longer write text into those image placeholders
- the PptxGenJS fixtures still emit `OBJECT` placeholders instead of raw OOXML `pic`, but the hardened runtime now treats those placeholders as image-capable slots

## Next Steps

- Use the mixed text-image fixtures as workflow automation alpha inputs and keep runtime changes scoped to regression-backed profiling fixes.
