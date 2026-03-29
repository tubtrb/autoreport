"""Prototype orchestration surface for v0.4 workflow automation ideas.

This module stays intentionally separate from the current CLI and web runtime.
It provides a richer design scaffold for automation that may sit on top of the
template inspection and report generation engine in a later promotion step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "AutomationAsset",
    "AutomationPlan",
    "AutomationStep",
    "AutomationTrigger",
    "build_template_report_automation_plan",
    "describe_plan",
    "plan_to_markdown",
    "summarize_manual_gates",
]


@dataclass(frozen=True)
class AutomationTrigger:
    """A branch-local description of what starts an automation flow."""

    name: str
    source: str
    cadence: str = "on_demand"


@dataclass(frozen=True)
class AutomationAsset:
    """One named input or output in the prototype automation contract."""

    name: str
    kind: str
    required: bool
    description: str


@dataclass(frozen=True)
class AutomationStep:
    """One orchestration step in the prototype automation plan."""

    step_id: str
    label: str
    actor: str
    action: str
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    approval_required: bool = False


@dataclass(frozen=True)
class AutomationPlan:
    """A richer output shape for workflow-automation experiments."""

    trigger: AutomationTrigger
    goal: str
    inputs: list[AutomationAsset]
    steps: list[AutomationStep]
    outputs: list[AutomationAsset]
    guardrails: list[str] = field(default_factory=list)


def build_template_report_automation_plan(
    trigger: AutomationTrigger,
    *,
    include_text_shaping: bool = False,
    include_human_review: bool = True,
    include_publish_handoff: bool = False,
) -> AutomationPlan:
    """Build a prototype plan for template-driven report automation."""

    inputs = [
        AutomationAsset(
            name="template_source",
            kind="pptx_or_template_name",
            required=True,
            description=(
                "PowerPoint template path or a supported logical template name."
            ),
        ),
        AutomationAsset(
            name="report_brief",
            kind="yaml_json_or_structured_notes",
            required=True,
            description=(
                "Source content that should become a template-driven report."
            ),
        ),
        AutomationAsset(
            name="delivery_policy",
            kind="workflow_preferences",
            required=False,
            description=(
                "Rules for optional review, publishing, and artifact retention."
            ),
        ),
    ]
    if include_text_shaping:
        inputs.append(
            AutomationAsset(
                name="text_shaping_policy",
                kind="style_constraints",
                required=False,
                description=(
                    "Optional tone, audience, or summarization rules for AI-assisted drafting."
                ),
            )
        )

    steps = [
        AutomationStep(
            step_id="inspect_template",
            label="Inspect template contract",
            actor="engine",
            action=(
                "Profile the selected template and export the machine-readable "
                "contract plus starter payload skeletons."
            ),
            consumes=["template_source"],
            produces=["template_contract", "payload_skeleton"],
            notes=[
                "Keep this step read-only against the source template.",
                "Surface template_id early so downstream steps can lock to it.",
            ],
        ),
        AutomationStep(
            step_id="draft_payload",
            label="Draft report payload",
            actor="automation",
            action=(
                "Map the report brief into the template-driven payload shape."
            ),
            consumes=["report_brief", "template_contract", "payload_skeleton"],
            produces=["draft_payload"],
        ),
    ]

    if include_text_shaping:
        steps.append(
            AutomationStep(
                step_id="shape_text",
                label="Shape text for audience and tone",
                actor="ai",
                action=(
                    "Optionally rewrite or compress draft text while preserving "
                    "the template contract and section intent."
                ),
                consumes=["draft_payload", "text_shaping_policy"],
                produces=["shaped_payload"],
                notes=[
                    "Keep the original draft payload available for diff or rollback.",
                    "Do not change template_id, slot counts, or slide ordering.",
                ],
            )
        )

    validation_input = "shaped_payload" if include_text_shaping else "draft_payload"
    steps.append(
        AutomationStep(
            step_id="validate_payload",
            label="Validate payload against template contract",
            actor="engine",
            action=(
                "Verify required fields, template_id alignment, and generation "
                "compatibility before any PPTX output is produced."
            ),
            consumes=[validation_input, "template_contract"],
            produces=["validated_payload"],
        )
    )
    steps.append(
        AutomationStep(
            step_id="generate_pptx",
            label="Generate editable PPTX artifact",
            actor="engine",
            action=(
                "Run the existing generation engine with the validated payload "
                "and persist a reviewable PPTX artifact."
            ),
            consumes=["validated_payload", "template_source"],
            produces=["generated_pptx"],
        )
    )

    if include_human_review:
        steps.append(
            AutomationStep(
                step_id="review_artifact",
                label="Review generated deck",
                actor="human",
                action=(
                    "Confirm visible slide content, template fidelity, and any "
                    "warnings before external distribution."
                ),
                consumes=["generated_pptx"],
                produces=["review_notes"],
                approval_required=True,
                notes=[
                    "This gate is the default stop before publication or handoff.",
                ],
            )
        )

    if include_publish_handoff:
        handoff_inputs = ["generated_pptx"]
        if include_human_review:
            handoff_inputs.append("review_notes")
        steps.append(
            AutomationStep(
                step_id="handoff_publish",
                label="Prepare publish or handoff packet",
                actor="automation",
                action=(
                    "Bundle the approved artifact, metadata, and operator notes "
                    "for downstream delivery automation."
                ),
                consumes=handoff_inputs,
                produces=["publish_packet"],
            )
        )

    outputs = [
        AutomationAsset(
            name="validated_payload",
            kind="report_payload",
            required=True,
            description=(
                "Template-aligned payload ready for deterministic generation."
            ),
        ),
        AutomationAsset(
            name="generated_pptx",
            kind="pptx",
            required=True,
            description="Editable deck artifact produced by the generation engine.",
        ),
    ]
    if include_human_review:
        outputs.append(
            AutomationAsset(
                name="review_notes",
                kind="approval_record",
                required=False,
                description=(
                    "Operator notes that explain whether the artifact is safe to ship."
                ),
            )
        )
    if include_publish_handoff:
        outputs.append(
            AutomationAsset(
                name="publish_packet",
                kind="handoff_bundle",
                required=False,
                description=(
                    "Automation-ready bundle for posting, delivery, or downstream publishing."
                ),
            )
        )

    guardrails = [
        "Keep the experiment branch-local until interface and rollout risk are explicit.",
        "Treat template inspection as the source of truth for template_id and slot shape.",
        "Preserve deterministic generation once the payload passes validation.",
        "Emit absolute-path evidence records so orchestration adapters can review artifacts without guessing.",
    ]
    if include_text_shaping:
        guardrails.append(
            "AI text shaping is advisory and must not silently change contract structure."
        )
    if include_human_review:
        guardrails.append(
            "Require human review before distribution outside the local experiment lane."
        )

    return AutomationPlan(
        trigger=trigger,
        goal=(
            "Turn a template source and report brief into a reviewable "
            "template-driven PPTX without wiring the experiment into the "
            "current runtime entrypoints."
        ),
        inputs=inputs,
        steps=steps,
        outputs=outputs,
        guardrails=guardrails,
    )


def describe_plan(plan: AutomationPlan) -> str:
    """Return a compact summary for notes and validation output."""

    return (
        f"{plan.trigger.name} from {plan.trigger.source} "
        f"({plan.trigger.cadence}): {len(plan.inputs)} inputs, "
        f"{len(plan.steps)} steps, {len(plan.outputs)} outputs"
    )


def summarize_manual_gates(plan: AutomationPlan) -> list[str]:
    """Return the labels of steps that require explicit approval."""

    return [
        step.label
        for step in plan.steps
        if step.approval_required
    ]


def plan_to_markdown(plan: AutomationPlan) -> str:
    """Render the prototype plan as compact Markdown for design notes."""

    lines = [
        f"# {plan.trigger.name}",
        "",
        f"- Goal: {plan.goal}",
        f"- Trigger source: {plan.trigger.source}",
        f"- Trigger cadence: {plan.trigger.cadence}",
        "",
        "## Inputs",
    ]
    lines.extend(
        f"- `{asset.name}` ({asset.kind}, required={str(asset.required).lower()}): "
        f"{asset.description}"
        for asset in plan.inputs
    )
    lines.append("")
    lines.append("## Steps")
    lines.extend(
        f"- `{step.step_id}` [{step.actor}] {step.label}: {step.action}"
        for step in plan.steps
    )
    lines.append("")
    lines.append("## Outputs")
    lines.extend(
        f"- `{asset.name}` ({asset.kind}): {asset.description}"
        for asset in plan.outputs
    )
    if plan.guardrails:
        lines.append("")
        lines.append("## Guardrails")
        lines.extend(f"- {guardrail}" for guardrail in plan.guardrails)
    return "\n".join(lines)
