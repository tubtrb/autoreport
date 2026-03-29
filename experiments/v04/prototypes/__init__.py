"""Scaffold package for isolated v0.4 prototypes."""

from .workflow_automation_spike import (
    AutomationAsset,
    AutomationPlan,
    AutomationStep,
    AutomationTrigger,
    build_template_report_automation_plan,
    describe_plan,
    plan_to_markdown,
    summarize_manual_gates,
)
from .workflow_automation_reporting import (
    finalize_workflow_automation_run,
)

__all__ = [
    "AutomationAsset",
    "AutomationPlan",
    "AutomationStep",
    "AutomationTrigger",
    "build_template_report_automation_plan",
    "describe_plan",
    "finalize_workflow_automation_run",
    "plan_to_markdown",
    "summarize_manual_gates",
]
