# v0.4 Incubator 2 Migration Ledger

This ledger compares the older `codex/v0.4-incubator` experiment set against
the current `codex/v0.3-master` product baseline.

Comparison axes:

- product framing
- payload and contract compatibility
- dependency on current runtime surfaces
- validation coverage
- whether the artifact assumes `weekly_report` semantics

## Decisions

| Source artifact | Class | Decision | Incubator2 action |
| --- | --- | --- | --- |
| `design/README.md` | design | `carry_retarget` | keep as active framing, rewrite around `autoreport_editorial` |
| `design/branch-boundaries.md` | design | `carry_retarget` | keep branch-local boundary rules, update for `incubator2` |
| `design/pptxgenjs-template-authoring-spike.md` | design | `carry_retarget` | keep the authoring spike, rewrite around current contract-first flow |
| `design/pptxgenjs-editorial-template-translation.md` | design | `carry_retarget` | keep the reference-translation memo, remove weekly wording |
| `design/pptxgenjs-image-placeholder-followup-spike.md` | design | `carry_retarget` | keep the diagnostic framing, point it at current public surfaces |
| `design/workflow-automation-orchestration.md` | design | `carry_retarget` | keep the orchestration framing, rebuild it around `inspect_template_contract` plus `scaffold_payload` |
| `notes/README.md` | notes | `leave_behind` | do not create an active notes lane in `incubator2` |
| `prototypes/__init__.py` | prototype | `carry_as_is` | copy unchanged |
| `prototypes/README.md` | prototype | `carry_retarget` | keep the prototype guardrails, rewrite around the current engine |
| `prototypes/richer_layout_spike.py` | prototype | `carry_as_is` | copy unchanged |
| `prototypes/text_shaping_spike.py` | prototype | `carry_as_is` | copy unchanged |
| `prototypes/workflow_automation_spike.py` | prototype | `carry_retarget` | keep the interface, change the narrative to contract-first editorial automation |
| `prototypes/workflow_automation_sandbox.py` | prototype | `carry_retarget` | rebuild around `inspect_template_contract`, `scaffold_payload`, and `generate_report_from_mapping` |
| `prototypes/pptxgenjs_template_spike/package.json` | tooling | `carry_retarget` | keep prototype-local Node workspace for internal authoring only |
| `prototypes/pptxgenjs_template_spike/package-lock.json` | tooling | `carry_retarget` | keep lockfile |
| `prototypes/pptxgenjs_template_spike/.gitignore` | tooling | `carry_as_is` | keep `node_modules/` ignored |
| `prototypes/pptxgenjs_template_spike/generate_templates.mjs` | tooling | `carry_retarget` | keep generator, remove weekly framing text, and scope it to internal template authoring |
| `prototypes/pptxgenjs_template_spike/template_specs.json` | tooling | `carry_retarget` | keep template matrix, update descriptions and editorial preview copy |
| `prototypes/pptxgenjs_template_spike/validate_templates.py` | tooling | `carry_retarget` | rebuild validation around `inspect_template_contract` and scaffolded payloads |
| `prototypes/pptxgenjs_template_spike/image_placeholder_followup.py` | tooling | `carry_retarget` | keep the diagnostic path, retarget to current payload and contract shapes |
| `prototypes/pptxgenjs_template_spike/presentationgo_reference_analysis.py` | tooling | `carry_retarget` | keep local reference analysis for first-party template design inputs |
| `prototypes/pptxgenjs_template_spike/assets/*.png` | asset | `carry_as_is` | copy unchanged |
| `prototypes/pptxgenjs_template_spike/generated/*.pptx` | fixture | `carry_retarget` | keep as active branch-local fixtures after fresh regeneration |
| `sandboxes/README.md` | sandbox | `carry_retarget` | recreate as editorial-only |
| `sandboxes/.gitignore` | sandbox | `carry_retarget` | keep generated folders ignored |
| `sandboxes/demo-run-001/**/*` | sandbox | `leave_behind` | rebuild from scratch with Autoreport-introduction content |
| `sandboxes/design-preview-001/**/*` | sandbox | `leave_behind` | do not copy the old weekly preview |
| `validation/README.md` | validation | `carry_retarget` | keep validation posture, tie it to fresh `incubator2` runs |
| `validation/workflow-automation-checklist.md` | validation | `carry_retarget` | keep the promotion checks, remove weekly assumptions |
| `validation/bootstrap-checklist.md` | validation | `leave_behind` | old bootstrap status is not active evidence in `incubator2` |
| `validation/pptxgenjs-template-authoring-report.md` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `validation/pptxgenjs-template-authoring-evidence.json` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `validation/pptxgenjs-image-placeholder-followup-report.md` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `validation/pptxgenjs-image-placeholder-followup-evidence.json` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `validation/presentationgo-reference-analysis.md` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `validation/presentationgo-reference-analysis.json` | validation | `leave_behind` | replace with fresh `incubator2` run output |
| `tests/test_v04_prototype_scaffolds.py` | test | `carry_as_is` | copy unchanged |
| `tests/test_workflow_automation_spike.py` | test | `carry_retarget` | keep intent, remove weekly trigger names |
| `tests/test_workflow_automation_sandbox.py` | test | `carry_retarget` | rewrite around editorial payload structure |
| `tests/test_pptxgenjs_template_spike.py` | test | `carry_retarget` | retarget to scaffolded editorial-compatible payloads |
| `tests/test_pptxgenjs_image_placeholder_followup.py` | test | `carry_retarget` | retarget to image-ref based generation |
| `tests/test_pptxgenjs_reference_design.py` | test | `carry_retarget` | retarget to editorial-compatible assertions |

## Deferred work

- runtime patch to stop image-capable placeholders from being treated as text
  candidates
- promotion of any `v0.4` prototype into `autoreport/`
- public release framing or product claims
