from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autoreport.loader import parse_yaml_text
from autoreport.template_flow import serialize_document
from tests.verif_test import chatgpt as chatgpt_module
from tests.verif_test.chatgpt import (
    _assistant_text_looks_like_user_echo,
    _assistant_reply_ready_for_return,
    _assistant_text_ready_for_return,
    _transport_submission_started,
    _transport_growth_grace_polls,
    ControllerMetrics,
    _assistant_reply_progressed,
    _build_transport_failure_message,
    _button_meta_is_exact_send,
    _button_meta_is_voice_input,
    _candidate_priority,
    _classify_session_reason,
    _detect_no_sandbox,
    _select_best_page_candidate,
    _wait_for_manual_recovery,
    canonical_profile_dir,
    collect_chatgpt_response,
    collect_chatgpt_response_once,
    normalize_yaml_candidate,
)
from tests.verif_test.catalog import build_prepared_sample, expand_suite
from tests.verif_test.pipeline import (
    _is_retryable_http_failure,
    _run_checker_with_retry,
    execute_suite_run,
    is_yaml_extract_failure,
    record_visual_review,
    select_review_queue,
)
from tests.verif_test.release_gate import (
    _transport_budget_for_sample,
    build_release_gate_plan,
    execute_release_gate_run,
    prepare_release_gate_samples,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION = "extai-chatgpt-spot"


def _ready_session_report() -> dict[str, object]:
    expected_profile_dir = str(canonical_profile_dir(DEFAULT_SESSION))
    return {
        "ok": True,
        "session": DEFAULT_SESSION,
        "launcher": "manual_chrome_cdp_attach",
        "reason": "ready",
        "message": "session ready",
        "expected_profile_dir": expected_profile_dir,
        "actual_profile_dir": expected_profile_dir,
        "legacy_recovery_source": str(
            (REPO_ROOT / "output" / "playwright" / "chrome-userdata-copy").resolve()
        ),
        "browser_status": "open",
        "browser_type": "chrome",
        "headed": "true",
        "browser_pid": 4321,
        "cdp_endpoint": "http://127.0.0.1:9222",
        "no_sandbox_detected": False,
        "page_url": "https://chatgpt.com/c/demo",
        "page_title": "Regression Ready",
        "selected_page_url": "https://chatgpt.com/c/demo",
        "selected_page_title": "Regression Ready",
        "has_composer": True,
        "has_new_chat_button": True,
        "has_send_button": True,
        "tabs": [
            {
                "index": 0,
                "current": True,
                "title": "Regression Ready",
                "url": "https://chatgpt.com/c/demo",
            }
        ],
        "page_candidates": [
            {
                "index": 0,
                "url": "https://chatgpt.com/c/demo",
                "title": "Regression Ready",
                "has_composer": True,
                "has_new_chat_button": True,
                "has_send_button": True,
                "has_login_prompt": False,
                "has_human_check": False,
                "body_excerpt": "",
                "assistant_message_count": 0,
                "user_message_count": 0,
                "ready": True,
                "priority": 0,
                "selected": True,
            }
        ],
        "recent_response_failures": [],
        "bootstrap_actions": ["attach-only manual chrome"],
        "manual_prepare_commands": ["manual chrome open"],
    }


def _write_session_artifacts(artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "session-page.txt").write_text("demo\n", encoding="utf-8")
    (artifact_dir / "session-network.jsonl").write_text("", encoding="utf-8")
    (artifact_dir / "session-screenshot.png").write_bytes(b"png")


class _FakePage:
    def __init__(self, url: str, title: str) -> None:
        self.url = url
        self._title = title

    def title(self) -> str:
        return self._title


class _FakeController:
    def __init__(self) -> None:
        self.metrics = ControllerMetrics()
        self.no_sandbox_detected = False
        self.selected_page = _FakePage("https://chatgpt.com/c/demo", "Recovered")
        self.ensure_calls: list[tuple[str | None, bool]] = []
        self.run_calls = 0

    def ensure_ready(
        self,
        *,
        navigation_mode: str | None = None,
        relaunch: bool = False,
        **_: object,
    ):
        self.ensure_calls.append((navigation_mode, relaunch))
        return {
            "ok": True,
            "selected_page_url": self.selected_page.url,
            "selected_page_title": self.selected_page.title(),
            "recent_response_failures": [],
            "no_sandbox_detected": False,
        }

    def run_transport_once(self, **_: object) -> str:
        self.run_calls += 1
        if self.run_calls == 1:
            raise RuntimeError("first transport failed")
        return "report_content:\n  title_slide:\n    pattern_id: cover.manual"

    def _recent_transport_response_failures(self) -> list[dict[str, object]]:
        return []


class VerifTestCatalogTestCase(unittest.TestCase):
    def test_expand_suite_uses_canonical_case_order(self) -> None:
        smoke_cases = expand_suite("smoke")
        regression_cases = expand_suite("regression")
        full_cases = expand_suite("full")

        self.assertEqual(
            [case.case_id for case in smoke_cases],
            [
                "01_one_image_canary",
                "01_two_image_canary",
                "01_three_image_canary",
            ],
        )
        self.assertEqual(regression_cases[-1].case_id, "05_dense_text_canary")
        self.assertEqual(full_cases[-1].case_id, "10_full_family_canary")

    def test_prepared_sample_uses_full_manual_prompt_and_generated_starter(self) -> None:
        case = expand_suite("smoke")[0]
        sample = build_prepared_sample(case)

        self.assertTrue(sample.prompt.startswith("# Complete the starter YAML below as the final answer."))
        self.assertIn("Autoreport Manual Regression 01_one_image_canary", sample.prompt)
        self.assertIn("report_content:", sample.prompt)
        self.assertIn("# End of starter YAML.", sample.prompt)
        self.assertIn("text_image.manual.procedure.one", sample.starter_yaml)
        self.assertEqual(sample.manifest["image_ref_count"], 1)

    def test_yaml_extract_failure_helper_flags_parse_error_payload(self) -> None:
        payload = {
            "ok": False,
            "error_type": "yaml_parse_error",
            "message": "Failed to parse YAML: boom",
            "_http_status": 400,
        }

        self.assertTrue(is_yaml_extract_failure(payload))

    def test_review_queue_uses_fixed_representative_case_ids(self) -> None:
        rows = [
            {
                "case_id": "01_one_image_canary",
                "label": "One Image Canary",
                "failure_class": None,
                "review_required": True,
                "review_decision": None,
                "artifact_pptx": "one.pptx",
                "slide_count": 3,
            },
            {
                "case_id": "05_balanced_canary",
                "label": "Five Slide Balanced Canary",
                "failure_class": None,
                "review_required": True,
                "review_decision": None,
                "artifact_pptx": "five.pptx",
                "slide_count": 7,
            },
            {
                "case_id": "10_full_family_canary",
                "label": "Ten Slide Full Family Canary",
                "failure_class": None,
                "review_required": True,
                "review_decision": None,
                "artifact_pptx": "ten.pptx",
                "slide_count": 12,
            },
        ]

        regression_queue = select_review_queue(rows, suite_name="regression")
        full_queue = select_review_queue(rows, suite_name="full")
        release_gate_queue = select_review_queue(rows, suite_name="release-gate")

        self.assertEqual(
            [item["case_id"] for item in regression_queue],
            ["01_one_image_canary", "05_balanced_canary"],
        )
        self.assertEqual(
            [item["case_id"] for item in full_queue],
            ["01_one_image_canary", "05_balanced_canary", "10_full_family_canary"],
        )
        self.assertEqual(
            [item["case_id"] for item in release_gate_queue],
            ["01_one_image_canary", "05_balanced_canary", "10_full_family_canary"],
        )


class VerifTestTransportContractTestCase(unittest.TestCase):
    def test_normalize_yaml_candidate_unwraps_yaml_code_fence(self) -> None:
        raw_turn = """YAML

Here is the completed draft.

```yaml
report_content:
  title_slide:
    pattern_id: cover.manual
    slots:
      doc_title: Demo
```

This matches the requested schema.
"""

        candidate = normalize_yaml_candidate(raw_turn)

        self.assertEqual(
            candidate,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                    "    slots:",
                    "      doc_title: Demo",
                ]
            ),
        )

    def test_normalize_yaml_candidate_wraps_rootless_snippet(self) -> None:
        raw_turn = "\n".join(
            [
                "title_slide:",
                "  pattern_id: cover.manual",
                "  slots:",
                "    doc_title: Demo",
            ]
        )

        candidate = normalize_yaml_candidate(raw_turn)

        self.assertEqual(
            candidate,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                    "    slots:",
                    "      doc_title: Demo",
                ]
            ),
        )

    def test_page_selection_prefers_ready_conversation_tab(self) -> None:
        candidates = [
            {
                "index": 0,
                "url": "https://chatgpt.com/",
                "priority": _candidate_priority(
                    url="https://chatgpt.com/",
                    has_composer=True,
                    has_new_chat_button=True,
                    remembered_url=None,
                ),
            },
            {
                "index": 1,
                "url": "https://chatgpt.com/c/abc",
                "priority": _candidate_priority(
                    url="https://chatgpt.com/c/abc",
                    has_composer=True,
                    has_new_chat_button=True,
                    remembered_url=None,
                ),
            },
        ]

        selected = _select_best_page_candidate(candidates, remembered_url=None)

        self.assertIsNotNone(selected)
        self.assertEqual(selected["index"], 1)

    def test_page_selection_falls_back_to_remembered_url(self) -> None:
        remembered_url = "https://chatgpt.com/c/remembered"
        candidates = [
            {
                "index": 0,
                "url": remembered_url,
                "priority": _candidate_priority(
                    url=remembered_url,
                    has_composer=False,
                    has_new_chat_button=False,
                    remembered_url=remembered_url,
                ),
            },
            {
                "index": 1,
                "url": "https://chatgpt.com/",
                "priority": _candidate_priority(
                    url="https://chatgpt.com/",
                    has_composer=False,
                    has_new_chat_button=False,
                    remembered_url=remembered_url,
                ),
            },
        ]

        selected = _select_best_page_candidate(candidates, remembered_url=remembered_url)

        self.assertIsNotNone(selected)
        self.assertEqual(selected["url"], remembered_url)

    def test_detect_no_sandbox_processes(self) -> None:
        processes = [
            {"CommandLine": "chrome.exe --profile-directory demo"},
            {"CommandLine": "chrome.exe --no-sandbox --profile-directory demo"},
        ]

        self.assertTrue(_detect_no_sandbox(processes))

    def test_ready_dom_with_chat_requirements_403_is_challenge_blocked(self) -> None:
        reason = _classify_session_reason(
            selected_candidate={
                "url": "https://chatgpt.com/c/demo",
                "title": "Regression Ready",
                "body_excerpt": "",
                "has_composer": True,
                "has_new_chat_button": True,
                "has_human_check": False,
                "has_login_prompt": False,
            },
            recent_response_failures=[
                {
                    "status": 403,
                    "url": "https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare",
                }
            ],
            no_sandbox_detected=False,
        )

        self.assertEqual(reason, "challenge_blocked")

    def test_manual_recovery_wait_can_turn_blocked_session_ready(self) -> None:
        initial_report = {
            **_ready_session_report(),
            "ok": False,
            "reason": "challenge_blocked",
            "message": "blocked",
        }
        progress_messages: list[str] = []

        recovered = _wait_for_manual_recovery(
            initial_report=initial_report,
            refresh=_ready_session_report,
            timeout_seconds=1.0,
            poll_seconds=0.0,
            log_interval_seconds=1.0,
            progress=progress_messages.append,
        )

        self.assertTrue(recovered["ok"])
        self.assertTrue(recovered["manual_intervention_used"])
        self.assertIn("Manual recovery succeeded", recovered["message"])
        self.assertTrue(progress_messages)

    def test_manual_recovery_wait_stays_finite_when_block_persists(self) -> None:
        initial_report = {
            **_ready_session_report(),
            "ok": False,
            "reason": "login_required",
            "message": "login required",
        }

        expired = _wait_for_manual_recovery(
            initial_report=initial_report,
            refresh=lambda: dict(initial_report),
            timeout_seconds=0.01,
            poll_seconds=0.0,
            log_interval_seconds=1.0,
            progress=None,
        )

        self.assertFalse(expired["ok"])
        self.assertTrue(expired["manual_intervention_used"])
        self.assertIn("Manual recovery window expired", expired["message"])

    def test_collect_chatgpt_response_retries_without_browser_relaunch(self) -> None:
        controller = _FakeController()

        with patch.object(chatgpt_module, "_controller_for_session", return_value=controller):
            response = collect_chatgpt_response(
                session=DEFAULT_SESSION,
                prompt="demo",
                send_wait_seconds=0.0,
                poll_seconds=0.0,
                max_polls=1,
            )

        self.assertIn("report_content:", response)
        self.assertEqual(controller.ensure_calls, [(None, False), (None, False)])
        self.assertEqual(controller.metrics.transport_attempts, 2)
        self.assertEqual(controller.metrics.session_relaunches, 0)

    def test_collect_chatgpt_response_once_uses_current_ready_page_only(self) -> None:
        class _OneShotController(_FakeController):
            def run_transport_once(self, **_: object) -> str:
                return "report_content:\n  title_slide:\n    pattern_id: cover.manual"

        controller = _OneShotController()

        with patch.object(chatgpt_module, "_controller_for_session", return_value=controller):
            response = collect_chatgpt_response_once(
                session=DEFAULT_SESSION,
                prompt="demo",
                send_wait_seconds=0.0,
                poll_seconds=0.0,
                max_polls=1,
            )

        self.assertIn("report_content:", response)
        self.assertEqual(controller.ensure_calls, [(None, False)])
        self.assertEqual(controller.metrics.transport_attempts, 1)
        self.assertEqual(controller.metrics.session_relaunches, 0)

    def test_assistant_reply_progressed_when_text_changes_without_count_bump(self) -> None:
        self.assertTrue(
            _assistant_reply_progressed(
                baseline_state={
                    "assistant_message_count": 1,
                    "last_assistant_text": "previous",
                },
                current_state={
                    "assistant_message_count": 1,
                    "last_assistant_text": "new reply body",
                },
            )
        )

    def test_assistant_text_flags_user_prompt_echo(self) -> None:
        self.assertTrue(
            _assistant_text_looks_like_user_echo(
                {
                    "last_assistant_text": (
                        "Keep the screenshot note short and tied to the visible result."
                    ),
                    "last_user_text": (
                        "# Prompt header\n"
                        "Keep the screenshot note short and tied to the visible "
                        "result.\n"
                        "Finish step 1 only after the completion cue is clearly "
                        "visible in the slide."
                    ),
                }
            )
        )

    def test_assistant_text_flags_unparseable_yaml_prefix_from_user_prompt(self) -> None:
        self.assertTrue(
            _assistant_text_looks_like_user_echo(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "title_slide:\n"
                        "pattern_id: cover.manual\n"
                        "slots:\n"
                        "doc_title: Demo\n"
                        "contents_slide:\n"
                        "pattern_id: contents.manual\n"
                        "slides:\n"
                        "pattern_id: text_image.manual.procedure.one\n"
                        "slots:\n"
                        "step_no: '1.1'\n"
                        "detail_body: 'Truncated value"
                    ),
                    "last_user_text": (
                        "# Prompt header\n"
                        "report_content:\n"
                        "  title_slide:\n"
                        "    pattern_id: cover.manual\n"
                        "    slots:\n"
                        "      doc_title: Demo\n"
                        "  contents_slide:\n"
                        "    pattern_id: contents.manual\n"
                        "  slides:\n"
                        "  - pattern_id: text_image.manual.procedure.one\n"
                        "    slots:\n"
                        "      step_no: '1.1'\n"
                        "      detail_body: 'Truncated value that continues in the starter.'"
                    ),
                }
            )
        )

    def test_assistant_text_allows_yaml_even_when_starter_overlaps_prompt(self) -> None:
        self.assertFalse(
            _assistant_text_looks_like_user_echo(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "  title_slide:\n"
                        "    pattern_id: cover.manual"
                    ),
                    "last_user_text": (
                        "# Prompt header\n"
                        "report_content:\n"
                        "  title_slide:\n"
                        "    pattern_id: cover.manual\n"
                        "  slides:\n"
                        "  - pattern_id: text_image.manual.procedure.one"
                    ),
                }
            )
        )

    def test_assistant_reply_ready_for_return_requires_parseable_yaml(self) -> None:
        self.assertFalse(
            _assistant_reply_ready_for_return(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "title_slide"
                    )
                }
            )
        )
        self.assertTrue(
            _assistant_reply_ready_for_return(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "  title_slide:\n"
                        "    pattern_id: cover.manual"
                    )
                }
            )
        )

    def test_assistant_reply_ready_for_return_requires_manifest_complete_yaml(self) -> None:
        expected_manifest = {
            "body_slide_count": 1,
            "pattern_order": ["text_image.manual.procedure.two"],
            "image_ref_count": 2,
        }

        self.assertFalse(
            _assistant_reply_ready_for_return(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "title_slide:\n"
                        "pattern_id: cover.manual\n"
                        "contents_slide:\n"
                        "pattern_id: contents.manual\n"
                        "slides:\n"
                        "pattern_id: text_image.manual.proce"
                    )
                },
                expected_manifest=expected_manifest,
            )
        )
        self.assertTrue(
            _assistant_reply_ready_for_return(
                {
                    "last_assistant_text": (
                        "report_content:\n"
                        "  title_slide:\n"
                        "    pattern_id: cover.manual\n"
                        "  contents_slide:\n"
                        "    pattern_id: contents.manual\n"
                        "  slides:\n"
                        "    - pattern_id: text_image.manual.procedure.two\n"
                        "      slots:\n"
                        "        image_1: image_1\n"
                        "        image_2: image_2"
                    )
                },
                expected_manifest=expected_manifest,
            )
        )

    def test_manifest_complete_yaml_echo_is_still_transport_ready(self) -> None:
        expected_manifest = {
            "body_slide_count": 1,
            "pattern_order": ["text_image.manual.procedure.one"],
            "image_ref_count": 1,
        }
        state = {
            "last_assistant_text": "\n".join(
                [
                    "report_content:",
                    "title_slide:",
                    "pattern_id: cover.manual",
                    "slots:",
                    "doc_title: Demo",
                    "contents_slide:",
                    "pattern_id: contents.manual",
                    "slots:",
                    "contents_title: Contents",
                    "contents_group_label: Demo",
                    "slides:",
                    "- pattern_id: text_image.manual.procedure.one",
                    "slots:",
                    "step_no: '1.1'",
                    "step_title: Demo Step",
                    "command_or_action: 'Action: validate the state.'",
                    "summary: Confirm the state.",
                    "detail_body: |-",
                    "Case demo uses the pattern for this step.",
                    "image_1: image_1",
                    "caption_1: Demo caption",
                ]
            ),
            "last_user_text": "\n".join(
                [
                    "# Prompt header",
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                    "    slots:",
                    "      doc_title: Demo",
                    "  contents_slide:",
                    "    pattern_id: contents.manual",
                    "    slots:",
                    "      contents_title: Contents",
                    "      contents_group_label: Demo",
                    "  slides:",
                    "    - pattern_id: text_image.manual.procedure.one",
                    "      slots:",
                    "        step_no: '1.1'",
                    "        step_title: Demo Step",
                    "        command_or_action: 'Action: validate the state.'",
                    "        summary: Confirm the state.",
                    "        detail_body: |-",
                    "          Case demo uses the pattern for this step.",
                    "        image_1: image_1",
                    "        caption_1: Demo caption",
                ]
            ),
        }
        self.assertTrue(_assistant_text_looks_like_user_echo(state))
        self.assertTrue(
            _assistant_reply_ready_for_return(
                state,
                expected_manifest=expected_manifest,
            )
        )

    def test_assistant_text_ready_for_return_rejects_stale_partial_yaml(self) -> None:
        expected_manifest = {
            "body_slide_count": 1,
            "pattern_order": ["text_image.manual.procedure.two"],
            "image_ref_count": 2,
        }
        self.assertFalse(
            _assistant_text_ready_for_return(
                "\n".join(
                    [
                        "report_content:",
                        "title_slide:",
                        "pattern_id: cover.manual",
                        "slots:",
                        "doc_title: Autoreport Manual Regression 01_two_image_canary",
                        "contents_slide:",
                        "pattern_id: contents.manual",
                        "slots:",
                        "contents_title: Contents",
                        "contents_group_label: Two Image Can",
                    ]
                ),
                expected_manifest=expected_manifest,
            )
        )

    def test_transport_growth_grace_polls_scale_with_manifest_complexity(self) -> None:
        self.assertEqual(_transport_growth_grace_polls(None), 0)
        self.assertEqual(
            _transport_growth_grace_polls(
                {"text_density": "balanced", "image_ref_count": 1}
            ),
            6,
        )
        self.assertEqual(
            _transport_growth_grace_polls(
                {"text_density": "dense", "image_ref_count": 3}
            ),
            8,
        )

    def test_transport_submission_started_detects_early_stream_without_send_button(self) -> None:
        self.assertTrue(
            _transport_submission_started(
                {
                    "has_send_button": False,
                    "has_stop_button": True,
                    "is_streaming": True,
                    "assistant_busy_count": 1,
                    "user_message_count": 1,
                }
            )
        )
        self.assertFalse(
            _transport_submission_started(
                {
                    "has_send_button": True,
                    "has_stop_button": False,
                    "is_streaming": False,
                    "assistant_busy_count": 0,
                    "user_message_count": 0,
                }
            )
        )

    def test_transport_failure_message_calls_out_prompt_echo(self) -> None:
        message = _build_transport_failure_message(
            {
                "last_assistant_text": (
                    "Keep the screenshot note short and tied to the visible result."
                ),
                "last_user_text": (
                    "# Prompt header\n"
                    "Keep the screenshot note short and tied to the visible "
                    "result.\n"
                    "Finish step 1 only after the completion cue is clearly "
                    "visible in the slide."
                ),
                "recent_response_failures": [],
            }
        )

        self.assertIn("prompt echoed", message)

    def test_button_meta_requires_exact_send_button(self) -> None:
        self.assertTrue(
            _button_meta_is_exact_send(
                {
                    "text": "",
                    "aria": "Send prompt",
                    "testid": "send-button",
                    "class_name": "composer-submit-btn",
                    "disabled": False,
                }
            )
        )
        self.assertFalse(
            _button_meta_is_exact_send(
                {
                    "text": "",
                    "aria": "Start voice mode",
                    "testid": "",
                    "class_name": "composer-submit-btn",
                    "disabled": False,
                }
            )
        )

    def test_button_meta_flags_voice_controls(self) -> None:
        self.assertTrue(
            _button_meta_is_voice_input(
                {
                    "text": "",
                    "aria": "Start voice mode",
                    "testid": "",
                    "class_name": "",
                    "disabled": False,
                }
            )
        )
        self.assertTrue(
            _button_meta_is_voice_input(
                {
                    "text": "",
                    "aria": "마이크 켜기",
                    "testid": "",
                    "class_name": "",
                    "disabled": False,
                }
            )
        )
        self.assertFalse(
            _button_meta_is_voice_input(
                {
                    "text": "",
                    "aria": "Send prompt",
                    "testid": "send-button",
                    "class_name": "",
                    "disabled": False,
                }
            )
        )

    def test_transport_failure_message_calls_out_ambiguous_voice_controls(self) -> None:
        message = _build_transport_failure_message(
            {
                "has_voice_input_button": True,
                "has_send_button": False,
            }
        )

        self.assertIn("voice or microphone controls", message)


class VerifTestPipelineIntegrationTestCase(unittest.TestCase):
    def test_local_success_run_writes_summary_transport_metrics_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                side_effect=lambda **_: build_prepared_sample(expand_suite("smoke")[0]).starter_yaml,
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={
                    "transport_attempts": 2,
                    "session_relaunches": 0,
                    "no_sandbox_detected": False,
                    "selected_page_url": "https://chatgpt.com/c/recovered",
                    "selected_page_title": "Recovered",
                    "recent_response_failures": [],
                },
            ):
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            case = summary["cases"][0]

            self.assertEqual(summary["overall_status"], "REVIEW")
            self.assertEqual(summary["launcher"], "manual_chrome_cdp_attach")
            self.assertEqual(case["transport_attempts"], 2)
            self.assertEqual(case["session_relaunches"], 0)
            self.assertEqual(case["selected_page_url"], "https://chatgpt.com/c/recovered")
            self.assertTrue((run_dir / "session-check.json").exists())
            self.assertTrue((run_dir / "session-page.txt").exists())
            self.assertTrue((run_dir / case["sample_id"] / "transport-state.json").exists())
            self.assertTrue((run_dir / case["sample_id"] / "transport-network.jsonl").exists())
            self.assertTrue((run_dir / case["sample_id"] / "transport-console.jsonl").exists())

            refreshed = record_visual_review(
                run_dir=run_dir,
                case_id="01_one_image_canary",
                decision="pass",
                note="visual ok",
            )
            self.assertEqual(refreshed["overall_status"], "PASS")

    def test_transport_failure_writes_transport_state_and_case_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                side_effect=RuntimeError("ChatGPT transport hit backend failure 403 at https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare."),
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={
                    "transport_attempts": 3,
                    "session_relaunches": 0,
                    "no_sandbox_detected": False,
                    "selected_page_url": "https://chatgpt.com/",
                    "selected_page_title": "Challenge",
                    "recent_response_failures": [
                        {
                            "status": 403,
                            "url": "https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare",
                        }
                    ],
                },
            ):
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            case = summary["cases"][0]
            self.assertEqual(case["failure_class"], "ai_transport_failure")
            self.assertEqual(case["stop_step"], "ai_transport")
            self.assertEqual(case["transport_attempts"], 3)
            self.assertEqual(case["session_relaunches"], 0)
            self.assertTrue(case["recent_response_failures"])
            self.assertTrue((run_dir / case["sample_id"] / "transport-state.json").exists())

    def test_checker_400_is_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.check_health",
                return_value={"ok": True, "message": "ok", "status_code": 200},
            ), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                side_effect=lambda **_: build_prepared_sample(expand_suite("smoke")[0]).starter_yaml,
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ), patch(
                "tests.verif_test.pipeline.run_manual_draft_check_http",
                return_value={
                    "ok": False,
                    "message": "Failed to parse YAML: bad indent",
                    "errors": [],
                    "warnings": [],
                    "summary": {},
                    "_http_status": 400,
                },
            ) as checker_mock:
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="http",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(checker_mock.call_count, 1)
            self.assertEqual(summary["cases"][0]["failure_class"], "yaml_extract_failure")

    def test_rootless_snippet_response_reaches_checker_after_yaml_wrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                return_value="title_slide:\n  pattern_id: cover.manual",
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ):
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            case = summary["cases"][0]
            self.assertEqual(case["failure_class"], "checker_failure")
            self.assertEqual(case["stop_step"], "checker")
            candidate = (run_dir / case["sample_id"] / "yaml-candidate.yaml").read_text(encoding="utf-8")
            self.assertTrue(candidate.startswith("report_content:\n  title_slide:"))

    def test_prose_only_response_stays_yaml_extract_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                return_value="Here is the completed draft in plain language only.",
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ):
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            case = summary["cases"][0]
            self.assertEqual(case["failure_class"], "yaml_extract_failure")
            self.assertEqual(case["stop_step"], "yaml_extract")

    def test_one_image_case_manifest_guard_fails_before_generate_on_extra_slide_and_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sample = build_prepared_sample(expand_suite("smoke")[0])
            mutated = parse_yaml_text(sample.starter_yaml)
            slides = mutated["report_content"]["slides"]
            slides.append(
                {
                    "pattern_id": "text_image.manual.procedure.one",
                    "slots": {
                        "step_no": "1.9",
                        "step_title": "Unexpected Extra Step",
                        "command_or_action": "Action: keep the slide count unchanged.",
                        "summary": "This extra slide should be blocked before generate.",
                        "detail_body": "The manifest guard should reject this drift.",
                        "image_1": "image_2",
                    },
                }
            )
            mutated_yaml = serialize_document(mutated, fmt="yaml").strip()

            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.check_health",
                return_value={"ok": True, "message": "ok", "status_code": 200},
            ), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                return_value=mutated_yaml,
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ), patch(
                "tests.verif_test.pipeline.run_manual_draft_check_http",
                return_value={
                    "ok": True,
                    "message": "Draft checker passed.",
                    "errors": [],
                    "warnings": [],
                    "summary": {
                        "body_slide_count": 5,
                        "blocking_issue_count": 0,
                        "warning_count": 0,
                    },
                    "_http_status": 200,
                },
            ), patch(
                "tests.verif_test.pipeline.run_generate_http",
            ) as generate_mock:
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="http",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            case = summary["cases"][0]
            self.assertEqual(case["failure_class"], "checker_failure")
            self.assertEqual(case["stop_step"], "checker")
            self.assertIn("Case manifest guard", case["checker_message"])
            self.assertEqual(generate_mock.call_count, 0)
            self.assertTrue((run_dir / case["sample_id"] / "manifest-guard.json").exists())

    def test_generate_500_retries_then_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.pipeline.check_health",
                return_value={"ok": True, "message": "ok", "status_code": 200},
            ), patch(
                "tests.verif_test.pipeline.collect_chatgpt_response",
                side_effect=lambda **_: build_prepared_sample(expand_suite("smoke")[0]).starter_yaml,
            ), patch(
                "tests.verif_test.pipeline.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ), patch(
                "tests.verif_test.pipeline.run_manual_draft_check_http",
                return_value={"ok": True, "message": "ok", "errors": [], "summary": {}, "_http_status": 200},
            ), patch(
                "tests.verif_test.pipeline.run_generate_http",
                return_value=(
                    {
                        "ok": False,
                        "status_code": 500,
                        "message": "boom",
                        "errors": [],
                    },
                    None,
                ),
            ) as generate_mock:
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    sample_count=1,
                    session=DEFAULT_SESSION,
                    mode="http",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(generate_mock.call_count, 3)
            self.assertEqual(summary["cases"][0]["failure_class"], "generate_failure")

    def test_checker_network_retry_succeeds_on_second_attempt(self) -> None:
        checker_payloads = [
            {
                "ok": False,
                "message": "Checker request failed: timeout",
                "errors": [],
                "warnings": [],
                "summary": {},
                "_http_status": 0,
            },
            {
                "ok": True,
                "message": "ok",
                "errors": [],
                "warnings": [],
                "summary": {},
                "_http_status": 200,
            },
        ]

        with patch(
            "tests.verif_test.pipeline.run_manual_draft_check_http",
            side_effect=checker_payloads,
        ) as checker_mock:
            payload = _run_checker_with_retry(
                mode="http",
                base_url="http://127.0.0.1:8000",
                yaml_candidate="report_content:\n  title_slide: {}",
            )

        self.assertEqual(checker_mock.call_count, 2)
        self.assertEqual(payload["attempts"], 2)
        self.assertTrue(payload["ok"])

    def test_session_check_only_writes_root_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(*, session: str, expected_profile_dir=None, artifact_dir=None):
                _ = (session, expected_profile_dir)
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.pipeline.inspect_chatgpt_session", side_effect=inspect_side_effect):
                run_dir = execute_suite_run(
                    suite_name="smoke",
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                    session_check_only=True,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["overall_status"], "PASS")
            self.assertEqual(summary["cases"], [])
            self.assertTrue((run_dir / "session-page.txt").exists())
            self.assertTrue((run_dir / "session-network.jsonl").exists())
            self.assertTrue((run_dir / "session-screenshot.png").exists())


class VerifTestReleaseGateTestCase(unittest.TestCase):
    def test_release_gate_plan_matches_fixed_20_chat_runbook(self) -> None:
        plan = build_release_gate_plan()

        self.assertEqual([chunk.name for chunk in plan], [
            "chunk_a_smoke",
            "chunk_b_regression",
            "chunk_c_full",
            "chunk_d_repeat",
        ])
        self.assertEqual([len(chunk.case_ids) for chunk in plan], [3, 5, 6, 6])
        self.assertEqual(sum(len(chunk.case_ids) for chunk in plan), 20)
        self.assertEqual(
            list(plan[-1].case_ids),
            [
                "01_one_image_canary",
                "05_balanced_canary",
                "10_full_family_canary",
                "05_dense_text_canary",
                "01_two_image_canary",
                "01_three_image_canary",
            ],
        )
        self.assertEqual([chunk.cooldown_after_seconds for chunk in plan], [300, 600, 900, 0])

    def test_release_gate_transport_budget_tunes_longer_cases(self) -> None:
        samples = prepare_release_gate_samples()
        three_image_sample = next(sample for sample in samples if sample.case_id == "01_three_image_canary")
        balanced_sample = next(sample for sample in samples if sample.case_id == "05_balanced_canary")
        dense_sample = next(sample for sample in samples if sample.case_id == "05_dense_text_canary")

        self.assertEqual(
            _transport_budget_for_sample(
                three_image_sample,
                send_wait_seconds=0.8,
                poll_seconds=3.0,
                max_polls=20,
            ).max_polls,
            28,
        )
        self.assertEqual(
            _transport_budget_for_sample(
                balanced_sample,
                send_wait_seconds=0.8,
                poll_seconds=3.0,
                max_polls=20,
            ).max_polls,
            32,
        )
        self.assertEqual(
            _transport_budget_for_sample(
                dense_sample,
                send_wait_seconds=0.8,
                poll_seconds=3.0,
                max_polls=20,
            ).max_polls,
            36,
        )

    def test_release_gate_default_transport_passes_expected_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def inspect_side_effect(
                *,
                session: str,
                expected_profile_dir=None,
                artifact_dir=None,
                allow_manual_recovery=True,
                bootstrap_attempts=None,
                progress=None,
            ):
                _ = (
                    session,
                    expected_profile_dir,
                    allow_manual_recovery,
                    bootstrap_attempts,
                    progress,
                )
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.release_gate.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.release_gate.collect_chatgpt_response_once",
                side_effect=RuntimeError("stop after first transport"),
            ) as collect_mock, patch(
                "tests.verif_test.release_gate.capture_chatgpt_transport_diagnostics",
                return_value={"transport_attempts": 1, "session_relaunches": 0},
            ), patch(
                "tests.verif_test.release_gate.export_chatgpt_transport_artifacts",
                return_value=None,
            ):
                execute_release_gate_run(
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                    sleep_fn=lambda _: None,
                )

        self.assertEqual(collect_mock.call_count, 1)
        kwargs = collect_mock.call_args.kwargs
        self.assertEqual(kwargs["expected_manifest"]["case_id"], "01_one_image_canary")
        self.assertEqual(kwargs["expected_manifest"]["image_ref_count"], 1)

    def test_release_gate_success_runs_one_session_with_fixed_cooldowns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sleep_calls: list[float] = []
            responses = iter(sample.starter_yaml for sample in prepare_release_gate_samples())

            def inspect_side_effect(
                *,
                session: str,
                expected_profile_dir=None,
                artifact_dir=None,
                allow_manual_recovery=True,
                bootstrap_attempts=None,
                progress=None,
            ):
                _ = (
                    session,
                    expected_profile_dir,
                    allow_manual_recovery,
                    bootstrap_attempts,
                    progress,
                )
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            with patch("tests.verif_test.release_gate.inspect_chatgpt_session", side_effect=inspect_side_effect), patch(
                "tests.verif_test.release_gate.check_health",
                return_value={"ok": True, "message": "ok", "status_code": 200},
            ):
                run_dir = execute_release_gate_run(
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                    transport=lambda sample: next(responses),
                    sleep_fn=sleep_calls.append,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["suite"], "release-gate")
            self.assertEqual(summary["runbook"], "chatgpt-web-low-trigger-release-gate-v1")
            self.assertEqual(summary["planned_chat_count"], 20)
            self.assertEqual(summary["completed_chat_count"], 20)
            self.assertEqual(summary["single_session_browser_relaunches"], 0)
            self.assertEqual(summary["guard_trip_reason"], "")
            self.assertEqual(
                [chunk["status"] for chunk in summary["chunk_results"]],
                ["PASS", "PASS", "PASS", "PASS"],
            )
            self.assertEqual(
                [item["seconds"] for item in summary["cooldown_schedule_applied"] if item["type"] == "chunk"],
                [300, 600, 900],
            )
            self.assertEqual(len(summary["cooldown_schedule_applied"]), 28)
            self.assertEqual(sleep_calls.count(45.0), 19)
            self.assertEqual(sleep_calls.count(180.0), 6)
            self.assertEqual(sleep_calls.count(300.0), 1)
            self.assertEqual(sleep_calls.count(600.0), 1)
            self.assertEqual(sleep_calls.count(900.0), 1)
            self.assertTrue((run_dir / "chunk-results.json").exists())
            self.assertTrue((run_dir / "chunk-results.md").exists())

    def test_release_gate_mid_run_guard_abort_blocks_remaining_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            call_counter = {"count": 0}
            success_responses = iter(sample.starter_yaml for sample in prepare_release_gate_samples())

            def inspect_side_effect(
                *,
                session: str,
                expected_profile_dir=None,
                artifact_dir=None,
                allow_manual_recovery=True,
                bootstrap_attempts=None,
                progress=None,
            ):
                _ = (
                    session,
                    expected_profile_dir,
                    allow_manual_recovery,
                    bootstrap_attempts,
                    progress,
                )
                if artifact_dir is not None:
                    _write_session_artifacts(Path(artifact_dir))
                return _ready_session_report()

            def transport_side_effect(sample) -> str:
                _ = sample
                call_counter["count"] += 1
                if call_counter["count"] == 6:
                    raise RuntimeError(
                        "ChatGPT transport hit backend failure 403 at https://chatgpt.com/backend-api/sentinel/chat-requirements/prepare."
                    )
                return next(success_responses)

            with patch("tests.verif_test.release_gate.inspect_chatgpt_session", side_effect=inspect_side_effect):
                run_dir = execute_release_gate_run(
                    session=DEFAULT_SESSION,
                    mode="local",
                    output_root=Path(temp_dir),
                    run_preflight=False,
                    transport=transport_side_effect,
                    sleep_fn=lambda _: None,
                )

            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["overall_status"], "FAIL")
            self.assertEqual(summary["completed_chat_count"], 5)
            self.assertEqual(
                summary["guard_trip_stage"],
                "chunk_b_regression:ai_transport",
            )
            self.assertIn("403", summary["guard_trip_reason"])
            self.assertEqual(
                [chunk["status"] for chunk in summary["chunk_results"]],
                ["PASS", "ABORTED", "BLOCKED", "BLOCKED"],
            )
            self.assertEqual(summary["chunk_results"][1]["completed_chat_count"], 2)
            self.assertEqual(len(summary["cases"]), 6)
            self.assertEqual(summary["cases"][-1]["failure_class"], "ai_transport_failure")


class VerifTestRetryHelperTestCase(unittest.TestCase):
    def test_retry_helper_only_retries_network_and_5xx_failures(self) -> None:
        self.assertTrue(
            _is_retryable_http_failure({"ok": False, "_http_status": 0}, status_key="_http_status")
        )
        self.assertTrue(
            _is_retryable_http_failure({"ok": False, "status_code": 503}, status_key="status_code")
        )
        self.assertFalse(
            _is_retryable_http_failure({"ok": False, "_http_status": 400}, status_key="_http_status")
        )
        self.assertFalse(
            _is_retryable_http_failure({"ok": True, "status_code": 500}, status_key="status_code")
        )


if __name__ == "__main__":
    unittest.main()
