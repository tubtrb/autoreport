"""Tests for the v0.4 workflow automation prototype surface."""

from __future__ import annotations

import unittest

from experiments.v04.prototypes.workflow_automation_spike import (
    AutomationTrigger,
    build_template_report_automation_plan,
    describe_plan,
    plan_to_markdown,
    summarize_manual_gates,
)


class WorkflowAutomationSpikeTestCase(unittest.TestCase):
    """Lock the branch-local workflow automation planning contract."""

    def test_default_plan_keeps_review_gate(self) -> None:
        trigger = AutomationTrigger(
            name="editorial-refresh",
            source="manual_run",
        )

        plan = build_template_report_automation_plan(trigger)

        self.assertEqual(
            [step.step_id for step in plan.steps],
            [
                "inspect_template",
                "draft_payload",
                "validate_payload",
                "generate_pptx",
                "review_artifact",
            ],
        )
        self.assertEqual(
            summarize_manual_gates(plan),
            ["Review generated deck"],
        )
        self.assertEqual(
            [asset.name for asset in plan.outputs],
            ["validated_payload", "generated_pptx", "review_notes"],
        )

    def test_optional_text_shaping_and_publish_handoff_expand_plan(self) -> None:
        trigger = AutomationTrigger(
            name="scheduled-external-share",
            source="scheduler",
            cadence="weekly",
        )

        plan = build_template_report_automation_plan(
            trigger,
            include_text_shaping=True,
            include_publish_handoff=True,
        )

        self.assertIn("text_shaping_policy", [asset.name for asset in plan.inputs])
        self.assertEqual(
            [step.step_id for step in plan.steps],
            [
                "inspect_template",
                "draft_payload",
                "shape_text",
                "validate_payload",
                "generate_pptx",
                "review_artifact",
                "handoff_publish",
            ],
        )
        self.assertEqual(
            [asset.name for asset in plan.outputs],
            [
                "validated_payload",
                "generated_pptx",
                "review_notes",
                "publish_packet",
            ],
        )
        self.assertIn(
            "AI text shaping is advisory and must not silently change contract structure.",
            plan.guardrails,
        )

    def test_markdown_and_summary_include_trigger_context(self) -> None:
        trigger = AutomationTrigger(
            name="template-automation-spike",
            source="webhook",
            cadence="event_driven",
        )

        plan = build_template_report_automation_plan(
            trigger,
            include_human_review=False,
        )

        self.assertEqual(
            describe_plan(plan),
            (
                "template-automation-spike from webhook (event_driven): "
                "3 inputs, 4 steps, 2 outputs"
            ),
        )
        markdown = plan_to_markdown(plan)
        self.assertIn("# template-automation-spike", markdown)
        self.assertIn("- Trigger source: webhook", markdown)
        self.assertIn("`generate_pptx` [engine] Generate editable PPTX artifact", markdown)


if __name__ == "__main__":
    unittest.main()
