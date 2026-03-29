# Workflow Automation Promotion Checklist

Prototype: `experiments/v04/prototypes/workflow_automation_spike.py`

## Interface checks

- Are trigger, input, step, and output shapes explicit enough for another tool
  or engineer to consume without guessing?
- Does the plan keep `template_contract` and `template_id` as first-class
  dependencies instead of hiding them inside free-form prompts?
- Are optional capabilities such as text shaping and publish handoff clearly
  marked as optional?
- Does each sandbox run emit `.codex/worker-status.json` with collector-compatible
  absolute artifact paths and a non-empty remaining-gap field?
- Is `.codex/worker-final.json` reserved for an explicit finalize step rather
  than the default sandbox run?

## Safety checks

- Does the orchestration keep deterministic validation before PPTX generation?
- Is there still an explicit human review gate before external distribution?
- Can the flow preserve a branch-local posture until rollout risk is known?
- Does the adapter avoid mixing git rebase/push/cleanup behavior into the
  content automation plan itself?

## Compatibility checks

- Can the prototype explain how it would reuse template inspection and current
  generation behavior without rewriting them?
- Are the outputs compatible with the current template-driven payload and PPTX
  artifact model?
- Can the sandbox rehearse both the built-in editorial path and a mixed
  user-template path without special-case runtime switches?
- Is it clear which parts are incubator-only and not yet part of CLI or web?
- Can the current `v0.3` collector validate the emitted `.codex` files without
  special-case logic?
- Does the adapter stay honest about discovery scope, meaning it emits
  collector-compatible files without claiming that the current `codex/v0.3-*`
  scanner will automatically discover `codex/v0.4-incubator2`?
- Is `.codex/master-next.txt` still treated as a separate master-thread
  instruction channel rather than something the sandbox run should emit or
  reinterpret?
- Do the docs preserve the upstream shared-broadcast rule, meaning branch-
  specific instructions belong in `.codex/master-next.txt` or
  `.codex/workstream.json`, not inside repeated user-facing handoffs?

## Decision

- Promote only if the interface is stable, evidence requirements are clear, and
  runtime integration boundaries are understood.
- Keep incubating if the plan is useful but still missing review semantics,
  delivery policy, failure mapping, or report-channel adapter rules.
- Stop if the automation model starts hiding too much product behavior behind
  opaque orchestration logic.
