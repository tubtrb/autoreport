# v0.4 PptxGenJS Image Placeholder Follow-up Spike

## Goal

This follow-up stays inside `experiments/v04/` and answers one narrow question:
is the `text-image` template failure primarily an authoring problem, a Python
profiler boundary problem, or both?

The runtime under `autoreport/` is out of scope for this spike. We are only
collecting evidence strong enough to decide whether a runtime patch is the next
step.

## Boundaries

- `PptxGenJS` is still being evaluated as a template authoring tool, not as a runtime replacement.
- `python-pptx` and the current Python generation path stay unchanged.
- No PowerPoint desktop/manual control is available in this environment, so the comparison uses:
  - the existing PptxGenJS baseline
  - follow-up PptxGenJS variants
  - one branch-local control fixture created from the default PowerPoint OOXML package

## Comparison Matrix

- Baseline: current `v04-text-image-template.pptx`
- Variant 1: same geometry, but asks PptxGenJS for a raw `pic` placeholder token
- Variant 2: same PptxGenJS placeholder path, but reduces image prominence so the body slot dominates the layout
- Control: default PowerPoint template rewritten into `title + body + pic + caption` so we can observe a true `pic` placeholder without leaving the branch

## Evidence Layers

The follow-up uses two independent layers:

1. OOXML placeholder inspection
- Dump master/layout/slide placeholder metadata from the `.pptx` package
- Record raw placeholder `type`, shape tag, and whether a text body exists

2. Current Python inspection/generation behavior
- `inspect_template_contract(...)`
- `scaffold_payload(...)`
- `generate_report_from_mapping(...)`
- re-open the generated deck with `python-pptx` and record where text actually landed

## Decision Rule

- `authoring_issue`: only the PptxGenJS-authored files show the problem, or a PptxGenJS recipe change removes it cleanly
- `profiler_issue`: even the control fixture with a real `pic` placeholder is still classified as a text target
- `mixed`: both of the above are true
- `inconclusive`: the evidence still cannot separate the causes

## Expected Outcome

The spike succeeds when the cause is classified reproducibly.
If the verdict is still ambiguous, keep the branch-local posture at
`viable_text_only` and do not touch the runtime yet.
