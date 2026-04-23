from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Error as PlaywrightError,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from autoreport.web.manual_ai_yaml import coerce_manual_ai_yaml_candidate
from autoreport.web.style_presets import MANUAL_PUBLIC_TEMPLATE_NAME
from tests.verif_test.catalog import validate_yaml_candidate_against_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHATGPT_SESSION = "extai-chatgpt-spot"
CANONICAL_PROFILE_ROOT = REPO_ROOT / ".codex" / "playwright" / "profiles"
LEGACY_RECOVERY_SOURCE = REPO_ROOT / "output" / "playwright" / "chrome-userdata-copy"
ROOT_CHATGPT_URL = "https://chatgpt.com/"
LAUNCHER_NAME = "manual_chrome_cdp_attach"
CHATGPT_BOOTSTRAP_ATTEMPTS = 3
CHATGPT_TRANSPORT_ATTEMPTS = 3
CHATGPT_MANUAL_RECOVERY_TIMEOUT_SECONDS = 180.0
CHATGPT_MANUAL_RECOVERY_POLL_SECONDS = 2.0
CHATGPT_MANUAL_RECOVERY_LOG_INTERVAL_SECONDS = 15.0
MANUAL_CDP_HOST = "127.0.0.1"
MANUAL_CDP_PORT = 9222
MONITORED_RESPONSE_MARKERS = (
    "/cdn-cgi/challenge-platform/",
    "/backend-api/sentinel/",
    "/backend-api/f/conversation/prepare",
    "/backend-api/sentinel/chat-requirements/prepare",
    "/api/auth/session",
    "/backend-api/me",
)
RETRYABLE_CHALLENGE_MARKERS = (
    "/cdn-cgi/challenge-platform/",
    "/backend-api/sentinel/",
    "/backend-api/f/conversation/prepare",
)
CONSOLE_CHALLENGE_MARKERS = (
    "enable javascript and cookies to continue",
    "cloudflare challenge",
    "turnstile",
    "pat challenge",
    "just a moment",
)
CONSOLE_LOGIN_MARKERS = (
    "/api/auth/session",
    "/backend-api/me",
    "account_bootstrap_forbidden",
    "/backend-api/accounts/check",
    "/backend-api/user_granular_consent",
)
CHALLENGE_TEXT_PATTERN = re.compile(
    r"verify you are human|checking your browser|just a moment|enable javascript and cookies to continue|cloudflare|turnstile|pat challenge",
    re.IGNORECASE,
)
LOGIN_TEXT_PATTERN = re.compile(
    r"log in|login|sign in|continue with google|continue with microsoft",
    re.IGNORECASE,
)
VOICE_CONTROL_PATTERN = re.compile(
    r"\b(mic|microphone|voice|audio|speech|dictat(?:e|ion)?|record|transcrib(?:e|ing)?|talk)\b|마이크|음성|녹음|말하기",
    re.IGNORECASE,
)
MANUAL_RECOVERY_REASONS = {"challenge_blocked", "login_required"}

_PROBE_PAGE_SCRIPT = """
() => {
  const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
  const normalizeMultiline = (value) => {
    const text = String(value || "").replace(/\\r\\n/g, "\\n").replace(/\\r/g, "\\n");
    return text
      .split("\\n")
      .map((line) => line.replace(/[ \\t]+/g, " ").trimEnd())
      .join("\\n")
      .replace(/\\n{3,}/g, "\\n\\n")
      .trim();
  };
  const truncate = (value, limit) => {
    const text = normalize(value);
    return text.length > limit ? text.slice(0, limit) : text;
  };
  const bodyText = document.body ? (document.body.innerText || document.body.textContent || "") : "";
  const title = document.title || "";
  const buttons = Array.from(document.querySelectorAll("button, a, [role='button']"));
  const buttonMeta = buttons.map((node) => ({
    text: normalize(node.innerText || node.textContent || ""),
    aria: node.getAttribute("aria-label") || "",
    testid: node.getAttribute("data-testid") || "",
    disabled: !!node.disabled,
  }));
  const controlBlob = buttonMeta
    .map((item) => [item.text, item.aria, item.testid].join(" ").toLowerCase())
    .join("\\n");
  const composer =
    document.querySelector("#prompt-textarea")
    || document.querySelector("textarea")
    || document.querySelector("[contenteditable='true']");
  const composerText = composer
    ? normalize(composer.innerText || composer.textContent || composer.value || "")
    : "";
  const hasNewChatButton = buttonMeta.some((item) =>
    /new chat/.test([item.text, item.aria, item.testid].join(" ").toLowerCase())
  );
  const isVoiceControl = (item) => {
    const text = [item.text, item.aria, item.testid].join(" ").toLowerCase();
    if (item.disabled || item.testid === "stop-button" || item.testid === "send-button") {
      return false;
    }
    return /(mic|microphone|voice|audio|speech|dictat|record|transcrib|talk|마이크|음성|녹음|말하기)/.test(text);
  };
  const hasSendButton = buttonMeta.some((item) =>
    !item.disabled && item.testid === "send-button"
  );
  const hasVoiceInputButton = buttonMeta.some((item) => isVoiceControl(item));
  const hasStopButton = buttonMeta.some((item) => {
    const text = [item.text, item.aria, item.testid].join(" ").toLowerCase();
    return item.testid === "stop-button" || /stop/.test(text);
  });
  const combinedText = [title, bodyText, controlBlob].join("\\n").toLowerCase();
  const hasLoginPrompt = /(log in|login|sign in|continue with google|continue with microsoft)/.test(combinedText);
  const hasHumanCheck = /(verify you are human|checking your browser|just a moment|enable javascript and cookies to continue|cloudflare|turnstile|pat challenge)/.test(combinedText);
  const assistantNodes = Array.from(document.querySelectorAll("[data-message-author-role='assistant']"));
  const userNodes = Array.from(document.querySelectorAll("[data-message-author-role='user']"));
  const extractAssistantText = (node) => {
    const codeBlocks = Array.from(node.querySelectorAll("pre"));
    const codeText = codeBlocks
      .map((block) => normalizeMultiline(block.innerText || block.textContent || ""))
      .filter((item) => item.length > 0);
    if (codeText.length) {
      return codeText.join("\\n\\n");
    }
    return normalizeMultiline(node.innerText || node.textContent || "");
  };
  const assistantMessages = assistantNodes
    .map((node, index) => {
      const text = extractAssistantText(node);
      return {
        id: node.id || `assistant-${index + 1}`,
        text,
        textLength: text.length,
        busy: false,
        streaming: false,
      };
    })
    .filter((item) => item.textLength > 0);
  const userMessages = userNodes
    .map((node, index) => {
      const text = normalizeMultiline(node.innerText || node.textContent || "");
      return {
        id: node.id || `user-${index + 1}`,
        text,
        textLength: text.length,
      };
    })
    .filter((item) => item.textLength > 0);
  const lastAssistant = assistantMessages.length
    ? assistantMessages[assistantMessages.length - 1]
    : null;
  const lastUser = userMessages.length
    ? userMessages[userMessages.length - 1]
    : null;
  return {
    readyState: document.readyState || "",
    url: location.href,
    title,
    bodyExcerpt: truncate(bodyText, 500),
    hasComposer: !!composer,
    composerText,
    hasSendButton,
    hasVoiceInputButton,
    hasStopButton,
    hasNewChatButton,
    hasLoginPrompt,
    hasHumanCheck,
    assistantMessageCount: assistantMessages.length,
    userMessageCount: userNodes.length,
    assistantBusyCount: hasStopButton ? 1 : 0,
    isStreaming: hasStopButton,
    lastAssistantText: lastAssistant ? lastAssistant.text : "",
    lastAssistantTextLength: lastAssistant ? lastAssistant.textLength : 0,
    assistantMessages,
    lastUserText: lastUser ? lastUser.text : "",
    lastUserTextLength: lastUser ? lastUser.textLength : 0,
    userMessages,
    controls: buttonMeta.slice(0, 20),
  };
}
"""

_SESSION_CONTROLLERS: dict[str, "ChatGPTBrowserController"] = {}


@dataclass
class PageCandidate:
    index: int
    url: str
    title: str
    has_composer: bool
    has_new_chat_button: bool
    has_send_button: bool
    has_login_prompt: bool
    has_human_check: bool
    body_excerpt: str
    assistant_message_count: int
    user_message_count: int
    ready: bool
    priority: int
    selected: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "url": self.url,
            "title": self.title,
            "has_composer": self.has_composer,
            "has_new_chat_button": self.has_new_chat_button,
            "has_send_button": self.has_send_button,
            "has_login_prompt": self.has_login_prompt,
            "has_human_check": self.has_human_check,
            "body_excerpt": self.body_excerpt,
            "assistant_message_count": self.assistant_message_count,
            "user_message_count": self.user_message_count,
            "ready": self.ready,
            "priority": self.priority,
            "selected": self.selected,
        }


@dataclass
class ControllerMetrics:
    transport_attempts: int = 0
    session_relaunches: int = 0
    selected_page_url: str = ""
    selected_page_title: str = ""
    recent_response_failures: list[dict[str, Any]] = field(default_factory=list)
    no_sandbox_detected: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "transport_attempts": self.transport_attempts,
            "session_relaunches": self.session_relaunches,
            "selected_page_url": self.selected_page_url,
            "selected_page_title": self.selected_page_title,
            "recent_response_failures": list(self.recent_response_failures),
            "no_sandbox_detected": self.no_sandbox_detected,
        }


class ChatGPTBrowserController:
    def __init__(self, *, session: str) -> None:
        self.session = session
        self.profile_dir = canonical_profile_dir(session)
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.registered_pages: set[int] = set()
        self.selected_page: Page | None = None
        self.page_candidates: list[PageCandidate] = []
        self.browser_pid: int | None = None
        self.no_sandbox_detected = False
        self.bootstrap_actions: list[str] = []
        self.attach_error = ""
        self.session_network_events: deque[dict[str, Any]] = deque(maxlen=800)
        self.session_console_events: deque[dict[str, Any]] = deque(maxlen=800)
        self.transport_network_events: list[dict[str, Any]] = []
        self.transport_console_events: list[dict[str, Any]] = []
        self.transport_capture_active = False
        self.metrics = ControllerMetrics()
        self.last_report: dict[str, Any] | None = None

    def close(self) -> None:
        playwright = self.playwright
        self.playwright = None
        self.browser = None
        self.context = None
        self.selected_page = None
        self.page_candidates = []
        self.registered_pages.clear()
        self.browser_pid = None
        self.no_sandbox_detected = False
        self.attach_error = ""
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass

    def bootstrap(
        self,
        *,
        navigation_mode: str | None = None,
        allow_manual_recovery: bool = False,
        max_attempts: int | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        last_report: dict[str, Any] | None = None
        manual_recovery_used = False
        attempt_budget = max_attempts or CHATGPT_BOOTSTRAP_ATTEMPTS
        for attempt in range(1, attempt_budget + 1):
            self.close()
            self.session_network_events.clear()
            self.session_console_events.clear()
            self.bootstrap_actions = []
            try:
                self._attach_context()
            except RuntimeError as exc:
                last_report = self._build_attach_failure_report(
                    attempt=attempt,
                    error=str(exc),
                )
                self.last_report = last_report
                continue
            self.metrics.no_sandbox_detected = self.no_sandbox_detected
            last_report = self._inspect_current_context(
                attempt=attempt,
                navigation_mode=navigation_mode,
            )
            self.last_report = last_report
            if (
                allow_manual_recovery
                and not manual_recovery_used
                and _requires_manual_recovery(last_report)
            ):
                last_report = _wait_for_manual_recovery(
                    initial_report=last_report,
                    refresh=lambda: self.ensure_ready(
                        relaunch=False,
                        allow_manual_recovery=False,
                    ),
                    timeout_seconds=CHATGPT_MANUAL_RECOVERY_TIMEOUT_SECONDS,
                    poll_seconds=CHATGPT_MANUAL_RECOVERY_POLL_SECONDS,
                    log_interval_seconds=CHATGPT_MANUAL_RECOVERY_LOG_INTERVAL_SECONDS,
                    progress=progress,
                )
                manual_recovery_used = True
                self.last_report = last_report
            if last_report["ok"] or self.no_sandbox_detected:
                return last_report
        assert last_report is not None
        return last_report

    def _attach_context(self) -> None:
        endpoint = manual_cdp_endpoint(self.session)
        self.attach_error = ""
        self.bootstrap_actions = [
            f"Attach to an already-open manual Chrome session at {endpoint}.",
            f"Expect the canonical profile directory {self.profile_dir}.",
        ]
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(
                endpoint,
                timeout=10_000,
            )
        except Exception as exc:
            processes = _list_profile_processes(self.profile_dir)
            self.browser_pid = _select_browser_pid(processes)
            self.no_sandbox_detected = _detect_no_sandbox(processes)
            self.attach_error = _build_attach_error_message(
                session=self.session,
                profile_dir=self.profile_dir,
                endpoint=endpoint,
                processes=processes,
                error=str(exc),
            )
            raise RuntimeError(self.attach_error) from exc
        contexts = list(self.browser.contexts if self.browser is not None else [])
        if not contexts:
            self.attach_error = (
                f"ChatGPT browser session '{self.session}' is reachable at {endpoint}, "
                "but Chrome has no attachable browser context yet. Keep the manual "
                "Chrome window open, finish loading ChatGPT, and retry."
            )
            raise RuntimeError(self.attach_error)
        self.context = contexts[0]
        self.context.on("page", self._register_page)
        for page in self.context.pages:
            self._register_page(page)
        processes = _list_profile_processes(self.profile_dir)
        self.browser_pid = _select_browser_pid(processes)
        self.no_sandbox_detected = _detect_no_sandbox(processes)

    def _inspect_current_context(
        self,
        *,
        attempt: int,
        navigation_mode: str | None,
    ) -> dict[str, Any]:
        _ = navigation_mode
        remembered_url = read_last_successful_url(self.session)
        self.page_candidates = self._collect_page_candidates(remembered_url=remembered_url)
        selected_candidate = _select_best_page_candidate(
            [candidate.as_dict() for candidate in self.page_candidates],
            remembered_url=remembered_url,
        )
        selected_index = int(selected_candidate["index"]) if selected_candidate else -1
        for candidate in self.page_candidates:
            candidate.selected = candidate.index == selected_index
        self.selected_page = (
            self.context.pages[selected_index]
            if self.context is not None and selected_index >= 0
            else None
        )
        failures = self._recent_response_failures()
        selected_dict = selected_candidate or {
            "url": "",
            "title": "",
            "has_composer": False,
            "has_new_chat_button": False,
            "has_send_button": False,
            "has_login_prompt": False,
            "has_human_check": False,
            "body_excerpt": "",
        }
        report = {
            "ok": False,
            "session": self.session,
            "launcher": LAUNCHER_NAME,
            "reason": "not_open",
            "message": "",
            "expected_profile_dir": str(self.profile_dir),
            "actual_profile_dir": str(self.profile_dir),
            "legacy_recovery_source": str(legacy_recovery_source()),
            "browser_status": "open" if self.context is not None else "closed",
            "browser_type": "chrome",
            "headed": "true",
            "browser_pid": self.browser_pid,
            "cdp_endpoint": manual_cdp_endpoint(self.session),
            "no_sandbox_detected": self.no_sandbox_detected,
            "page_url": str(selected_dict.get("url", "")),
            "page_title": str(selected_dict.get("title", "")),
            "selected_page_url": str(selected_dict.get("url", "")),
            "selected_page_title": str(selected_dict.get("title", "")),
            "page_body_excerpt": str(selected_dict.get("body_excerpt", "")),
            "has_composer": bool(selected_dict.get("has_composer")),
            "has_new_chat_button": bool(selected_dict.get("has_new_chat_button")),
            "has_send_button": bool(selected_dict.get("has_send_button")),
            "tabs": [
                {
                    "index": candidate.index,
                    "current": candidate.selected,
                    "title": candidate.title,
                    "url": candidate.url,
                }
                for candidate in self.page_candidates
            ],
            "page_candidates": [candidate.as_dict() for candidate in self.page_candidates],
            "recent_response_failures": failures,
            "bootstrap_attempts": attempt,
            "bootstrap_actions": list(self.bootstrap_actions),
            "manual_prepare_commands": manual_prepare_commands(self.session),
            "manual_intervention_used": False,
            "manual_intervention_timeout_seconds": 0.0,
            "manual_intervention_elapsed_seconds": 0.0,
            "attach_error": self.attach_error,
            "list_output": "manual Chrome CDP attach",
            "tab_list_output": _render_tab_list_output(self.page_candidates),
        }
        report["reason"] = _classify_session_reason(
            selected_candidate=selected_dict,
            recent_response_failures=failures,
            no_sandbox_detected=self.no_sandbox_detected,
        )
        report["ok"] = report["reason"] == "ready"
        report["message"] = _session_message(report)
        return report

    def _collect_page_candidates(self, *, remembered_url: str | None) -> list[PageCandidate]:
        assert self.context is not None
        candidates: list[PageCandidate] = []
        try:
            pages = list(self.context.pages)
        except Exception:
            return []
        for index, page in enumerate(pages):
            payload = _evaluate_page(page)
            if payload is None:
                continue
            candidate = PageCandidate(
                index=index,
                url=str(payload.get("url", "")),
                title=str(payload.get("title", "")),
                has_composer=bool(payload.get("hasComposer")),
                has_new_chat_button=bool(payload.get("hasNewChatButton")),
                has_send_button=bool(payload.get("hasSendButton")),
                has_login_prompt=bool(payload.get("hasLoginPrompt")),
                has_human_check=bool(payload.get("hasHumanCheck")),
                body_excerpt=str(payload.get("bodyExcerpt", "")),
                assistant_message_count=int(payload.get("assistantMessageCount", 0)),
                user_message_count=int(payload.get("userMessageCount", 0)),
                ready=bool(payload.get("hasComposer")) or bool(payload.get("hasNewChatButton")),
                priority=_candidate_priority(
                    url=str(payload.get("url", "")),
                    has_composer=bool(payload.get("hasComposer")),
                    has_new_chat_button=bool(payload.get("hasNewChatButton")),
                    remembered_url=remembered_url,
                ),
            )
            candidates.append(candidate)
        candidates.sort(key=lambda item: (item.priority, item.index))
        return candidates

    def _register_page(self, page: Page) -> None:
        page_id = id(page)
        if page_id in self.registered_pages:
            return
        self.registered_pages.add(page_id)
        page.on("console", lambda msg, page=page: self._record_console(page, msg))
        page.on("pageerror", lambda err, page=page: self._record_page_error(page, err))
        page.on("response", lambda response, page=page: self._record_response(page, response))
        page.on(
            "requestfailed",
            lambda request, page=page: self._record_request_failed(page, request),
        )

    def _record_console(self, page: Page, message: ConsoleMessage) -> None:
        location = message.location
        payload = {
            "ts": _timestamp(),
            "type": message.type,
            "text": message.text,
            "page_url": _safe_page_url(page),
            "source_url": location.get("url", "") if isinstance(location, dict) else "",
            "line": location.get("lineNumber", 0) if isinstance(location, dict) else 0,
        }
        self.session_console_events.append(payload)
        if self.transport_capture_active:
            self.transport_console_events.append(payload)

    def _record_page_error(self, page: Page, error: Exception) -> None:
        payload = {
            "ts": _timestamp(),
            "type": "pageerror",
            "text": str(error),
            "page_url": _safe_page_url(page),
            "source_url": "",
            "line": 0,
        }
        self.session_console_events.append(payload)
        if self.transport_capture_active:
            self.transport_console_events.append(payload)

    def _record_response(self, page: Page, response: Response) -> None:
        try:
            payload = {
                "ts": _timestamp(),
                "page_url": _safe_page_url(page),
                "url": response.url,
                "status": int(response.status),
                "method": response.request.method,
                "resource_type": response.request.resource_type,
            }
        except Exception:
            return
        self.session_network_events.append(payload)
        if self.transport_capture_active:
            self.transport_network_events.append(payload)

    def _record_request_failed(self, page: Page, request) -> None:
        failure = request.failure or {}
        payload = {
            "ts": _timestamp(),
            "page_url": _safe_page_url(page),
            "url": request.url,
            "status": 0,
            "method": request.method,
            "resource_type": request.resource_type,
            "error_text": failure.get("errorText", "") if isinstance(failure, dict) else str(failure),
        }
        self.session_network_events.append(payload)
        if self.transport_capture_active:
            self.transport_network_events.append(payload)

    def _recent_response_failures(self) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for item in list(self.session_network_events)[-120:]:
            url = str(item.get("url", ""))
            status = int(item.get("status", 0))
            if status < 400:
                continue
            if any(marker in url for marker in MONITORED_RESPONSE_MARKERS) or url.startswith(
                "https://challenges.cloudflare.com/"
            ):
                failures.append(dict(item))
        return failures[-30:]

    def _recent_transport_response_failures(self) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for item in self.transport_network_events[-120:]:
            url = str(item.get("url", ""))
            status = int(item.get("status", 0))
            if status < 400:
                continue
            if any(marker in url for marker in MONITORED_RESPONSE_MARKERS) or url.startswith(
                "https://challenges.cloudflare.com/"
            ):
                failures.append(dict(item))
        return failures[-30:]

    def _safe_goto(self, page: Page, url: str) -> None:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except (PlaywrightTimeoutError, PlaywrightError):
            return

    def ensure_ready(
        self,
        *,
        navigation_mode: str | None = None,
        relaunch: bool = False,
        allow_manual_recovery: bool = False,
        bootstrap_attempts: int | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        _ = relaunch
        if not self._has_live_context():
            return self.bootstrap(
                navigation_mode=navigation_mode,
                allow_manual_recovery=allow_manual_recovery,
                max_attempts=bootstrap_attempts,
                progress=progress,
            )
        self.page_candidates = self._collect_page_candidates(
            remembered_url=read_last_successful_url(self.session)
        )
        selected_candidate = _select_best_page_candidate(
            [candidate.as_dict() for candidate in self.page_candidates],
            remembered_url=read_last_successful_url(self.session),
        )
        selected_index = int(selected_candidate["index"]) if selected_candidate else -1
        for candidate in self.page_candidates:
            candidate.selected = candidate.index == selected_index
        self.selected_page = (
            self.context.pages[selected_index]
            if self.context is not None and selected_index >= 0
            else None
        )
        report = {
            **(self.last_report or {}),
            "ok": False,
            "session": self.session,
            "launcher": LAUNCHER_NAME,
            "browser_status": "open",
            "browser_type": "chrome",
            "headed": "true",
            "browser_pid": self.browser_pid,
            "cdp_endpoint": manual_cdp_endpoint(self.session),
            "no_sandbox_detected": self.no_sandbox_detected,
            "expected_profile_dir": str(self.profile_dir),
            "actual_profile_dir": str(self.profile_dir),
            "legacy_recovery_source": str(legacy_recovery_source()),
            "tabs": [
                {
                    "index": candidate.index,
                    "current": candidate.selected,
                    "title": candidate.title,
                    "url": candidate.url,
                }
                for candidate in self.page_candidates
            ],
            "page_candidates": [candidate.as_dict() for candidate in self.page_candidates],
            "recent_response_failures": self._recent_response_failures(),
            "bootstrap_actions": list(self.bootstrap_actions),
            "manual_prepare_commands": manual_prepare_commands(self.session),
            "manual_intervention_used": False,
            "manual_intervention_timeout_seconds": 0.0,
            "manual_intervention_elapsed_seconds": 0.0,
            "attach_error": self.attach_error,
        }
        selected = selected_candidate or {
            "url": "",
            "title": "",
            "has_composer": False,
            "has_new_chat_button": False,
            "has_send_button": False,
            "has_login_prompt": False,
            "has_human_check": False,
            "body_excerpt": "",
        }
        report.update(
            {
                "page_url": str(selected.get("url", "")),
                "page_title": str(selected.get("title", "")),
                "selected_page_url": str(selected.get("url", "")),
                "selected_page_title": str(selected.get("title", "")),
                "page_body_excerpt": str(selected.get("body_excerpt", "")),
                "has_composer": bool(selected.get("has_composer")),
                "has_new_chat_button": bool(selected.get("has_new_chat_button")),
                "has_send_button": bool(selected.get("has_send_button")),
            }
        )
        report["reason"] = _classify_session_reason(
            selected_candidate=selected,
            recent_response_failures=report["recent_response_failures"],
            no_sandbox_detected=self.no_sandbox_detected,
        )
        report["ok"] = report["reason"] == "ready"
        report["message"] = _session_message(report)
        self.last_report = report
        return report

    def _has_live_context(self) -> bool:
        if self.context is None:
            return False
        try:
            _ = list(self.context.pages)
        except Exception:
            return False
        return True

    def _build_attach_failure_report(
        self,
        *,
        attempt: int,
        error: str,
    ) -> dict[str, Any]:
        processes = _list_profile_processes(self.profile_dir)
        self.browser_pid = _select_browser_pid(processes)
        self.no_sandbox_detected = _detect_no_sandbox(processes)
        report = {
            "ok": False,
            "session": self.session,
            "launcher": LAUNCHER_NAME,
            "reason": "not_open",
            "message": error,
            "expected_profile_dir": str(self.profile_dir),
            "actual_profile_dir": str(self.profile_dir),
            "legacy_recovery_source": str(legacy_recovery_source()),
            "browser_status": "open" if processes else "closed",
            "browser_type": "chrome",
            "headed": "true",
            "browser_pid": self.browser_pid,
            "cdp_endpoint": manual_cdp_endpoint(self.session),
            "no_sandbox_detected": self.no_sandbox_detected,
            "page_url": "",
            "page_title": "",
            "selected_page_url": "",
            "selected_page_title": "",
            "page_body_excerpt": "",
            "has_composer": False,
            "has_new_chat_button": False,
            "has_send_button": False,
            "tabs": [],
            "page_candidates": [],
            "recent_response_failures": [],
            "bootstrap_attempts": attempt,
            "bootstrap_actions": list(self.bootstrap_actions),
            "manual_prepare_commands": manual_prepare_commands(self.session),
            "manual_intervention_used": False,
            "manual_intervention_timeout_seconds": 0.0,
            "manual_intervention_elapsed_seconds": 0.0,
            "attach_error": error,
            "list_output": "manual Chrome CDP attach",
            "tab_list_output": "### Result\n- no attached ChatGPT pages",
        }
        report["message"] = _session_message(report)
        return report

    def start_transport_capture(self) -> None:
        self.transport_capture_active = True
        self.transport_network_events = []
        self.transport_console_events = []

    def stop_transport_capture(self) -> None:
        self.transport_capture_active = False

    def run_transport_once(
        self,
        *,
        prompt: str,
        expected_manifest: dict[str, Any] | None,
        send_wait_seconds: float,
        poll_seconds: float,
        max_polls: int,
    ) -> str:
        if self.selected_page is None:
            raise RuntimeError("No selected ChatGPT page is available for transport.")
        page = self.selected_page
        self.start_transport_capture()
        try:
            self._prepare_fresh_chat(page)
            baseline_state = _probe_transport_state(page)
            self._clear_and_type_prompt(page, prompt)
            time.sleep(send_wait_seconds)
            if not self._click_exact_send_button(page):
                state = _probe_transport_state(page)
                state["recent_response_failures"] = self._recent_transport_response_failures()
                raise RuntimeError(_build_transport_failure_message(state))
            stable_hits = 0
            previous_text = ""
            last_non_empty_text = ""
            last_state = capture_chatgpt_transport_diagnostics(self.session)
            remaining_polls = int(max_polls)
            growth_grace_polls = _transport_growth_grace_polls(expected_manifest)
            growth_grace_used = False
            while remaining_polls > 0:
                remaining_polls -= 1
                time.sleep(poll_seconds)
                last_state = capture_chatgpt_transport_diagnostics(self.session)
                current_text = str(last_state["last_assistant_text"]).strip()
                if (
                    last_state["has_login_prompt"]
                    or last_state["has_human_check"]
                    or last_state["recent_response_failures"]
                ):
                    raise RuntimeError(_build_transport_failure_message(last_state))
                if _assistant_text_looks_like_user_echo(last_state):
                    if _assistant_reply_ready_for_return(
                        last_state,
                        expected_manifest=expected_manifest,
                    ):
                        write_last_successful_url(self.session, page.url)
                        return current_text
                    continue
                if not _assistant_reply_progressed(
                    baseline_state=baseline_state,
                    current_state=last_state,
                ):
                    continue
                text_grew = bool(current_text) and len(current_text) > len(previous_text)
                if current_text:
                    stable_hits = stable_hits + 1 if current_text == previous_text else 1
                    previous_text = current_text
                    last_non_empty_text = current_text
                    if not bool(last_state["is_streaming"]) and _assistant_reply_ready_for_return(
                        last_state,
                        expected_manifest=expected_manifest,
                    ):
                        write_last_successful_url(self.session, page.url)
                        return current_text
                    if (
                        stable_hits >= 2
                        and len(current_text) > 40
                        and _assistant_reply_ready_for_return(
                            last_state,
                            expected_manifest=expected_manifest,
                        )
                    ):
                        write_last_successful_url(self.session, page.url)
                        return current_text
                if (
                    remaining_polls == 0
                    and not growth_grace_used
                    and growth_grace_polls > 0
                    and bool(last_state["is_streaming"])
                    and text_grew
                ):
                    remaining_polls = growth_grace_polls
                    growth_grace_used = True
            if (
                last_non_empty_text
                and not bool(last_state["is_streaming"])
                and _assistant_text_ready_for_return(
                    last_non_empty_text,
                    expected_manifest=expected_manifest,
                )
            ):
                write_last_successful_url(self.session, page.url)
                return last_non_empty_text
            raise RuntimeError(_build_transport_failure_message(last_state))
        finally:
            self.stop_transport_capture()

    def _prepare_fresh_chat(self, page: Page) -> None:
        state = _probe_transport_state(page)
        state["recent_response_failures"] = self._recent_transport_response_failures()
        if (
            state["has_login_prompt"]
            or state["has_human_check"]
            or state["recent_response_failures"]
        ):
            raise RuntimeError(_build_transport_failure_message(state))
        if (
            "/c/" in page.url
            or int(state["assistant_message_count"]) > 0
            or int(state["user_message_count"]) > 0
        ):
            if not self._click_new_chat(page):
                self._safe_goto(page, ROOT_CHATGPT_URL)
            self._wait_for_ready_composer(page)
            return
        self._wait_for_ready_composer(page)

    def _wait_for_ready_composer(self, page: Page) -> None:
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            state = _probe_transport_state(page)
            state["recent_response_failures"] = self._recent_transport_response_failures()
            if (
                state["has_login_prompt"]
                or state["has_human_check"]
                or state["recent_response_failures"]
            ):
                raise RuntimeError(_build_transport_failure_message(state))
            if state["has_composer"]:
                return
            time.sleep(0.5)
        raise RuntimeError("ChatGPT composer did not become ready.")

    def _click_new_chat(self, page: Page) -> bool:
        try:
            button = page.locator("[data-testid='create-new-chat-button']").first
            if button.count():
                button.click(timeout=2_000)
                return True
        except Exception:
            pass
        script = (
            "() => {"
            "const button = Array.from(document.querySelectorAll('button, a, [role=\"button\"]')).find((node) => {"
            "  const text = [node.innerText || node.textContent || '', node.getAttribute('aria-label') || '', node.getAttribute('data-testid') || ''].join(' ').toLowerCase();"
            "  return /new chat/.test(text);"
            "});"
            "if (!button) return false;"
            "button.click();"
            "return true;"
            "}"
        )
        try:
            return bool(page.evaluate(script))
        except PlaywrightError:
            return False

    def _click_send_button(self, page: Page) -> bool:
        return self._click_exact_send_button(page)
        selector_candidates = (
            "[data-testid='send-button']",
            "button.composer-submit-btn",
            "button.composer-submit-button-color",
            "button[aria-label*='send' i]",
            "button[aria-label*='보내']",
        )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            for selector in selector_candidates:
                try:
                    button = page.locator(selector).first
                    if button.count() and button.is_visible():
                        button.click(timeout=2_000)
                        return True
                except Exception:
                    continue
            script = (
                "() => {"
                "const button = Array.from(document.querySelectorAll('button, [role=\"button\"]')).find((node) => {"
                "  const text = [node.innerText || node.textContent || '', node.getAttribute('aria-label') || '', node.getAttribute('data-testid') || ''].join(' ').toLowerCase();"
                "  const aria = (node.getAttribute('aria-label') || '').toLowerCase();"
                "  const testid = node.getAttribute('data-testid') || '';"
                "  const className = String(node.className || '');"
                "  if (node.disabled || testid === 'stop-button') return false;"
                "  return testid === 'send-button'"
                "    || /send/.test(text)"
                "    || /보내/.test(aria)"
                "    || className.includes('composer-submit-btn');"
                "});"
                "if (!button) return false;"
                "button.click();"
                "return true;"
                "}"
            )
            try:
                if bool(page.evaluate(script)):
                    return True
            except PlaywrightError:
                pass
            time.sleep(0.25)
        return False

    def _click_exact_send_button(self, page: Page) -> bool:
        selector = "button[data-testid='send-button']"
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            state = _probe_transport_state(page)
            if _transport_submission_started(state):
                return True
            if state["has_voice_input_button"] and not state["has_send_button"]:
                return False
            try:
                button = page.locator(selector).first
                if button.count() and button.is_visible() and button.is_enabled():
                    meta = {
                        "text": button.inner_text(timeout=500),
                        "aria": button.get_attribute("aria-label") or "",
                        "testid": button.get_attribute("data-testid") or "",
                        "class_name": button.get_attribute("class") or "",
                        "disabled": False,
                    }
                    if not _button_meta_is_exact_send(meta):
                        return False
                    button.click(timeout=2_000)
                    return True
            except Exception:
                pass
            script = (
                "() => {"
                "const button = document.querySelector('button[data-testid=\"send-button\"]');"
                "if (!button) return false;"
                "const text = [button.innerText || button.textContent || '', button.getAttribute('aria-label') || '', button.getAttribute('data-testid') || '', String(button.className || '')].join(' ').toLowerCase();"
                "if (button.disabled) return false;"
                "if (/(mic|microphone|voice|audio|speech|dictat|record|transcrib|talk|마이크|음성|녹음|말하기)/.test(text)) return false;"
                "button.click();"
                "return true;"
                "}"
            )
            try:
                if bool(page.evaluate(script)):
                    return True
            except PlaywrightError:
                pass
            time.sleep(0.25)
        return False

    def _clear_and_type_prompt(self, page: Page, prompt: str) -> None:
        normalized_prompt = prompt.replace("\r\n", "\n").replace("\r", "\n")
        script = (
            "() => {"
            "const composer = document.querySelector('#prompt-textarea')"
            "  || document.querySelector('textarea')"
            "  || document.querySelector('[contenteditable=\"true\"]');"
            "if (!composer) return { ok: false, reason: 'missing-composer' };"
            "composer.focus();"
            "return { ok: true, tagName: composer.tagName || '' };"
            "}"
        )
        result = page.evaluate(script)
        if not isinstance(result, dict) or not result.get("ok"):
            raise RuntimeError("Prompt insertion failed inside the ChatGPT composer.")
        if str(result.get("tagName", "")).upper() == "TEXTAREA":
            page.fill("#prompt-textarea", normalized_prompt)
        else:
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.insert_text(normalized_prompt)
        read_text_script = (
            "() => {"
            "const composer = document.querySelector('#prompt-textarea')"
            "  || document.querySelector('textarea')"
            "  || document.querySelector('[contenteditable=\"true\"]');"
            "if (!composer) return '';"
            "return composer.value || composer.innerText || composer.textContent || '';"
            "}"
        )
        composer_text = str(page.evaluate(read_text_script)).replace("\u00a0", " ").strip()
        if not composer_text:
            raise RuntimeError("Prompt insertion failed; composer text is empty.")
        lines = normalized_prompt.splitlines()
        if not lines:
            return
        first_line = lines[0].strip()
        last_line = lines[-1].strip()
        if first_line and first_line not in composer_text:
            raise RuntimeError(
                "Prompt insertion failed; first line is missing from the composer."
            )
        if last_line and last_line not in composer_text:
            raise RuntimeError(
                "Prompt insertion failed; last line is missing from the composer."
            )

    def export_session_artifacts(self, artifact_dir: Path) -> None:
        report = self.last_report or {}
        _write_text(
            artifact_dir / "session-page.txt",
            "\n".join(
                [
                    f"URL: {report.get('selected_page_url', '')}",
                    f"Title: {report.get('selected_page_title', '')}",
                    "",
                    str(report.get("page_body_excerpt", "")),
                ]
            ).strip()
            + "\n",
        )
        _write_jsonl(artifact_dir / "session-network.jsonl", list(self.session_network_events))
        _write_jsonl(artifact_dir / "session-console.jsonl", list(self.session_console_events))
        screenshot_path = artifact_dir / "session-screenshot.png"
        if self.selected_page is not None:
            try:
                screenshot_path.write_bytes(
                    self.selected_page.screenshot(full_page=False, timeout=10_000)
                )
                return
            except Exception:
                pass
        screenshot_path.write_bytes(b"")

    def export_transport_artifacts(self, artifact_dir: Path) -> None:
        _write_jsonl(artifact_dir / "transport-network.jsonl", self.transport_network_events)
        _write_jsonl(artifact_dir / "transport-console.jsonl", self.transport_console_events)


def canonical_profile_dir(session: str) -> Path:
    return (CANONICAL_PROFILE_ROOT / session).resolve(strict=False)


def _transport_growth_grace_polls(expected_manifest: dict[str, Any] | None) -> int:
    if not expected_manifest:
        return 0
    text_density = str(expected_manifest.get("text_density", "") or "").lower()
    image_ref_count = int(expected_manifest.get("image_ref_count", 0) or 0)
    grace_polls = 0
    if image_ref_count >= 3:
        grace_polls = max(grace_polls, 4)
    if text_density == "balanced":
        grace_polls = max(grace_polls, 6)
    elif text_density == "dense":
        grace_polls = max(grace_polls, 8)
    return grace_polls


def legacy_recovery_source() -> Path:
    return LEGACY_RECOVERY_SOURCE.resolve(strict=False)


def last_successful_url_path(session: str) -> Path:
    return (
        REPO_ROOT / ".codex" / "playwright" / f"{session}-last-url.txt"
    ).resolve(strict=False)


def read_last_successful_url(session: str) -> str | None:
    path = last_successful_url_path(session)
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def write_last_successful_url(session: str, url: str) -> None:
    if not url.startswith("https://chatgpt.com/"):
        return
    path = last_successful_url_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(url.strip() + "\n", encoding="utf-8")


def manual_cdp_port(session: str) -> int:
    _ = session
    return MANUAL_CDP_PORT


def manual_cdp_endpoint(session: str) -> str:
    return f"http://{MANUAL_CDP_HOST}:{manual_cdp_port(session)}"


def manual_prepare_commands(session: str) -> list[str]:
    profile_dir = canonical_profile_dir(session)
    port = manual_cdp_port(session)
    return [
        '$chrome = "${env:ProgramFiles}\\Google\\Chrome\\Application\\chrome.exe"',
        "if (-not (Test-Path $chrome)) {",
        '  $chrome = "${env:ProgramFiles(x86)}\\Google\\Chrome\\Application\\chrome.exe"',
        "}",
        f'& $chrome --remote-debugging-port={port} --user-data-dir="{profile_dir}" "https://chatgpt.com/"',
        "# keep this Chrome window open, finish login/challenge, open one real ChatGPT conversation,",
        "# optionally send one short message, then rerun -SessionCheckOnly or the suite wrapper",
    ]


def _requires_manual_recovery(report: dict[str, Any]) -> bool:
    return (
        not bool(report.get("ok"))
        and not bool(report.get("no_sandbox_detected"))
        and str(report.get("reason", "")) in MANUAL_RECOVERY_REASONS
    )


def _assistant_reply_progressed(
    *,
    baseline_state: dict[str, Any],
    current_state: dict[str, Any],
) -> bool:
    baseline_count = int(baseline_state.get("assistant_message_count", 0) or 0)
    current_count = int(current_state.get("assistant_message_count", 0) or 0)
    if current_count > baseline_count:
        return True
    baseline_text = str(baseline_state.get("last_assistant_text", "") or "").strip()
    current_text = str(current_state.get("last_assistant_text", "") or "").strip()
    return bool(current_text) and current_text != baseline_text


def _wait_for_manual_recovery(
    *,
    initial_report: dict[str, Any],
    refresh: Callable[[], dict[str, Any]],
    timeout_seconds: float,
    poll_seconds: float,
    log_interval_seconds: float,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    if not _requires_manual_recovery(initial_report) or timeout_seconds <= 0:
        return dict(initial_report)
    if progress is not None:
        progress(
            "[manual-ai] session requires manual approval/login in the already-open Chrome window; "
            f"waiting up to {int(timeout_seconds)}s for ChatGPT to become ready"
        )
    started = time.monotonic()
    deadline = started + timeout_seconds
    next_log = started + max(log_interval_seconds, poll_seconds, 1.0)
    latest = dict(initial_report)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(max(poll_seconds, 0.0), remaining))
        latest = dict(refresh())
        elapsed = time.monotonic() - started
        if latest.get("ok"):
            latest["manual_intervention_used"] = True
            latest["manual_intervention_timeout_seconds"] = float(timeout_seconds)
            latest["manual_intervention_elapsed_seconds"] = round(elapsed, 1)
            latest["message"] = (
                f"{latest.get('message', '')} Manual recovery succeeded after {elapsed:.1f}s."
            ).strip()
            return latest
        if progress is not None and time.monotonic() >= next_log:
            page_url = str(latest.get("selected_page_url") or latest.get("page_url") or "")
            progress(
                "[manual-ai] still waiting for manual ChatGPT approval/login: "
                f"reason={latest.get('reason', 'unknown')} page={page_url}"
            )
            next_log = time.monotonic() + max(log_interval_seconds, poll_seconds, 1.0)
    elapsed = time.monotonic() - started
    latest["manual_intervention_used"] = True
    latest["manual_intervention_timeout_seconds"] = float(timeout_seconds)
    latest["manual_intervention_elapsed_seconds"] = round(elapsed, 1)
    latest["message"] = (
        f"{latest.get('message', '')} Manual recovery window expired after {elapsed:.1f}s."
    ).strip()
    return latest


def inspect_chatgpt_session(
    *,
    session: str,
    expected_profile_dir: Path | None = None,
    artifact_dir: Path | None = None,
    allow_manual_recovery: bool = False,
    bootstrap_attempts: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    controller = _controller_for_session(session)
    expected_dir = (
        expected_profile_dir or canonical_profile_dir(session)
    ).resolve(strict=False)
    report = controller.bootstrap(
        allow_manual_recovery=allow_manual_recovery,
        max_attempts=bootstrap_attempts,
        progress=progress,
    )
    report["expected_profile_dir"] = str(expected_dir)
    report["actual_profile_dir"] = str(controller.profile_dir)
    report["bootstrap_actions"] = list(controller.bootstrap_actions)
    report["manual_prepare_commands"] = manual_prepare_commands(session)
    if artifact_dir is not None:
        controller.export_session_artifacts(artifact_dir)
    return report


def ensure_chatgpt_session_ready(session: str) -> None:
    report = inspect_chatgpt_session(session=session)
    if not report["ok"]:
        raise RuntimeError(report["message"])


def collect_chatgpt_response(
    *,
    session: str,
    prompt: str,
    expected_manifest: dict[str, Any] | None = None,
    send_wait_seconds: float,
    poll_seconds: float,
    max_polls: int,
) -> str:
    controller = _controller_for_session(session)
    controller.metrics = ControllerMetrics(
        no_sandbox_detected=controller.no_sandbox_detected
    )
    last_error: RuntimeError | None = None
    for attempt_index in range(1, CHATGPT_TRANSPORT_ATTEMPTS + 1):
        controller.metrics.transport_attempts = attempt_index
        report = controller.ensure_ready(
            navigation_mode=None,
            relaunch=False,
            allow_manual_recovery=False,
            bootstrap_attempts=1,
        )
        controller.metrics.no_sandbox_detected = bool(report.get("no_sandbox_detected"))
        controller.metrics.selected_page_url = str(report.get("selected_page_url", ""))
        controller.metrics.selected_page_title = str(report.get("selected_page_title", ""))
        controller.metrics.recent_response_failures = list(
            report.get("recent_response_failures", [])
        )
        if not report["ok"]:
            last_error = RuntimeError(report["message"])
            continue
        try:
            response = controller.run_transport_once(
                prompt=prompt,
                expected_manifest=expected_manifest,
                send_wait_seconds=send_wait_seconds,
                poll_seconds=poll_seconds,
                max_polls=max_polls,
            )
            controller.metrics.recent_response_failures = (
                controller._recent_transport_response_failures()
            )
            if controller.selected_page is not None:
                controller.metrics.selected_page_url = controller.selected_page.url
                try:
                    controller.metrics.selected_page_title = controller.selected_page.title()
                except Exception:
                    controller.metrics.selected_page_title = ""
            return response
        except RuntimeError as exc:
            controller.metrics.recent_response_failures = (
                controller._recent_transport_response_failures()
            )
            if controller.selected_page is not None:
                controller.metrics.selected_page_url = controller.selected_page.url
                try:
                    controller.metrics.selected_page_title = controller.selected_page.title()
                except Exception:
                    controller.metrics.selected_page_title = ""
            last_error = exc
    assert last_error is not None
    raise last_error


def collect_chatgpt_response_once(
    *,
    session: str,
    prompt: str,
    expected_manifest: dict[str, Any] | None = None,
    send_wait_seconds: float,
    poll_seconds: float,
    max_polls: int,
) -> str:
    controller = _controller_for_session(session)
    controller.metrics = ControllerMetrics(
        no_sandbox_detected=controller.no_sandbox_detected
    )
    controller.metrics.transport_attempts = 1
    report = controller.ensure_ready(
        navigation_mode=None,
        relaunch=False,
        allow_manual_recovery=False,
        bootstrap_attempts=1,
    )
    controller.metrics.no_sandbox_detected = bool(report.get("no_sandbox_detected"))
    controller.metrics.selected_page_url = str(report.get("selected_page_url", ""))
    controller.metrics.selected_page_title = str(report.get("selected_page_title", ""))
    controller.metrics.recent_response_failures = list(
        report.get("recent_response_failures", [])
    )
    if not report["ok"]:
        raise RuntimeError(report["message"])
    try:
        response = controller.run_transport_once(
            prompt=prompt,
            expected_manifest=expected_manifest,
            send_wait_seconds=send_wait_seconds,
            poll_seconds=poll_seconds,
            max_polls=max_polls,
        )
    except RuntimeError:
        controller.metrics.recent_response_failures = (
            controller._recent_transport_response_failures()
        )
        if controller.selected_page is not None:
            controller.metrics.selected_page_url = controller.selected_page.url
            try:
                controller.metrics.selected_page_title = controller.selected_page.title()
            except Exception:
                controller.metrics.selected_page_title = ""
        raise
    controller.metrics.recent_response_failures = (
        controller._recent_transport_response_failures()
    )
    if controller.selected_page is not None:
        controller.metrics.selected_page_url = controller.selected_page.url
        try:
            controller.metrics.selected_page_title = controller.selected_page.title()
        except Exception:
            controller.metrics.selected_page_title = ""
    return response


def close_chatgpt_session(session: str) -> None:
    controller = _SESSION_CONTROLLERS.pop(session, None)
    if controller is not None:
        controller.close()


def get_chatgpt_transport_metrics(session: str) -> dict[str, Any]:
    controller = _SESSION_CONTROLLERS.get(session)
    if controller is None:
        return {
            "transport_attempts": 0,
            "session_relaunches": 0,
            "selected_page_url": "",
            "selected_page_title": "",
            "recent_response_failures": [],
            "no_sandbox_detected": False,
        }
    return controller.metrics.as_dict()


def export_chatgpt_transport_artifacts(session: str, artifact_dir: Path) -> None:
    controller = _SESSION_CONTROLLERS.get(session)
    if controller is None:
        _write_jsonl(artifact_dir / "transport-network.jsonl", [])
        _write_jsonl(artifact_dir / "transport-console.jsonl", [])
        return
    controller.export_transport_artifacts(artifact_dir)


def probe_chatgpt_session_state(session: str) -> dict[str, Any]:
    controller = _SESSION_CONTROLLERS.get(session)
    if controller is None or controller.selected_page is None:
        return {
            "ready_state": "",
            "href": "",
            "title": "",
            "has_composer": False,
            "has_new_chat_button": False,
            "has_send_button": False,
            "has_login_prompt": False,
            "has_human_check": False,
        }
    payload = _evaluate_page(controller.selected_page) or {}
    return {
        "ready_state": str(payload.get("readyState", "")),
        "href": str(payload.get("url", "")),
        "title": str(payload.get("title", "")),
        "has_composer": bool(payload.get("hasComposer")),
        "has_new_chat_button": bool(payload.get("hasNewChatButton")),
        "has_send_button": bool(payload.get("hasSendButton")),
        "has_login_prompt": bool(payload.get("hasLoginPrompt")),
        "has_human_check": bool(payload.get("hasHumanCheck")),
    }


def probe_chatgpt_transport_state(session: str) -> dict[str, Any]:
    controller = _SESSION_CONTROLLERS.get(session)
    if controller is None or controller.selected_page is None:
        return _empty_transport_state()
    payload = _probe_transport_state(controller.selected_page)
    return {
        **payload,
        "recent_response_failures": controller._recent_transport_response_failures(),
    }


def capture_chatgpt_transport_diagnostics(session: str) -> dict[str, Any]:
    state = probe_chatgpt_transport_state(session)
    metrics = get_chatgpt_transport_metrics(session)
    controller = _SESSION_CONTROLLERS.get(session)
    console_events = controller.transport_console_events if controller is not None else []
    network_events = controller.transport_network_events if controller is not None else []
    return {
        **state,
        **metrics,
        "recent_console_errors": _summarize_console_events(console_events),
        "console_events": list(console_events),
        "network_events": list(network_events),
    }


def normalize_yaml_candidate(raw_turn_text: str) -> str:
    coercion = coerce_manual_ai_yaml_candidate(
        raw_turn_text,
        built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
    )
    return (coercion.normalized_yaml or "").strip()


def raw_eval(session: str, expression: str, *, timeout: float = 30.0) -> Any:
    _ = timeout
    controller = _controller_for_session(session)
    report = controller.ensure_ready()
    if not report["ok"]:
        raise RuntimeError(report["message"])
    assert controller.selected_page is not None
    return controller.selected_page.evaluate(expression)


def _controller_for_session(session: str) -> ChatGPTBrowserController:
    controller = _SESSION_CONTROLLERS.get(session)
    if controller is None:
        controller = ChatGPTBrowserController(session=session)
        _SESSION_CONTROLLERS[session] = controller
    return controller


def _select_best_page_candidate(
    candidates: list[dict[str, Any]],
    *,
    remembered_url: str | None,
) -> dict[str, Any] | None:
    _ = remembered_url
    if not candidates:
        return None
    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            int(item.get("priority", 99)),
            int(item.get("index", 999)),
        ),
    )
    for candidate in sorted_candidates:
        candidate["selected"] = False
    selected = sorted_candidates[0]
    selected["selected"] = True
    return selected


def _candidate_priority(
    *,
    url: str,
    has_composer: bool,
    has_new_chat_button: bool,
    remembered_url: str | None,
) -> int:
    ready = has_composer or has_new_chat_button
    is_conversation = url.startswith("https://chatgpt.com/c/")
    is_chatgpt = url.startswith("https://chatgpt.com/")
    if is_conversation and ready:
        return 0
    if is_chatgpt and ready:
        return 1
    if remembered_url and _normalize_url(url) == _normalize_url(remembered_url):
        return 2
    if is_chatgpt:
        return 3
    return 99


def _classify_session_reason(
    *,
    selected_candidate: dict[str, Any],
    recent_response_failures: list[dict[str, Any]],
    no_sandbox_detected: bool,
) -> str:
    url = str(selected_candidate.get("url", ""))
    title = str(selected_candidate.get("title", ""))
    body_excerpt = str(selected_candidate.get("body_excerpt", ""))
    text = "\n".join([url, title, body_excerpt]).lower()
    failure_blob = "\n".join(
        f"{item.get('status', 0)} {item.get('url', '')}" for item in recent_response_failures
    ).lower()
    if no_sandbox_detected:
        return "challenge_blocked"
    if not url:
        return "not_open"
    if not url.startswith("https://chatgpt.com/"):
        return "wrong_page"
    if LOGIN_TEXT_PATTERN.search(text):
        return "login_required"
    if any(marker in failure_blob for marker in CONSOLE_LOGIN_MARKERS):
        return "login_required"
    if CHALLENGE_TEXT_PATTERN.search(text):
        return "challenge_blocked"
    if any(marker in failure_blob for marker in RETRYABLE_CHALLENGE_MARKERS):
        return "challenge_blocked"
    if bool(selected_candidate.get("has_human_check")):
        return "challenge_blocked"
    if bool(selected_candidate.get("has_login_prompt")):
        return "login_required"
    if bool(selected_candidate.get("has_composer")) or bool(
        selected_candidate.get("has_new_chat_button")
    ):
        return "ready"
    return "challenge_blocked"


def _session_message(report: dict[str, Any]) -> str:
    reason = str(report.get("reason", "not_open"))
    session = str(report.get("session", ""))
    url = str(report.get("selected_page_url") or report.get("page_url") or "")
    title = str(report.get("selected_page_title") or report.get("page_title") or "")
    pid = report.get("browser_pid")
    no_sandbox = bool(report.get("no_sandbox_detected"))
    attach_error = str(report.get("attach_error", "") or "").strip()
    if reason == "ready":
        return (
            f"ChatGPT browser session '{session}' is ready through the existing manual Chrome session. "
            f"Current page: {url!r} ({title!r}), browser_pid={pid!r}."
        )
    if no_sandbox:
        return (
            f"ChatGPT browser session '{session}' is running with '--no-sandbox', which is not allowed for the manual attach contract. "
            f"Current page: {url!r} ({title!r})."
        )
    if reason == "wrong_page":
        return (
            f"ChatGPT browser session '{session}' did not land on chatgpt.com. "
            f"Current page: {url!r} ({title!r})."
        )
    if reason == "login_required":
        return (
            f"ChatGPT browser session '{session}' reached ChatGPT, but the canonical profile still appears to require login. "
            f"Current page: {url!r} ({title!r})."
        )
    if reason == "challenge_blocked":
        return (
            f"ChatGPT browser session '{session}' reached ChatGPT with the canonical profile, but the UI is still blocked by a challenge or backend 401/403 watchdog failure. "
            f"Current page: {url!r} ({title!r})."
        )
    if attach_error:
        return attach_error
    return (
        f"ChatGPT browser session '{session}' is not attached to a manual Chrome session yet. "
        "Open Chrome manually with the canonical profile, keep it running, and rerun -SessionCheckOnly."
    )


def _render_tab_list_output(candidates: list[PageCandidate]) -> str:
    lines = ["### Result"]
    for candidate in candidates:
        current = " (current)" if candidate.selected else ""
        if candidate.url:
            lines.append(f"- {candidate.index}{current}: [{candidate.title}]({candidate.url})")
        else:
            lines.append(f"- {candidate.index}{current}: {candidate.title}")
    return "\n".join(lines)


def _empty_transport_state() -> dict[str, Any]:
    return {
        "page_url": "",
        "page_title": "",
        "body_excerpt": "",
        "has_composer": False,
        "composer_text": "",
        "has_send_button": False,
        "has_voice_input_button": False,
        "has_stop_button": False,
        "has_new_chat_button": False,
        "has_login_prompt": False,
        "has_human_check": False,
        "assistant_message_count": 0,
        "user_message_count": 0,
        "assistant_busy_count": 0,
        "is_streaming": False,
        "last_assistant_text": "",
        "last_assistant_text_length": 0,
        "assistant_messages": [],
        "last_user_text": "",
        "last_user_text_length": 0,
        "user_messages": [],
        "controls": [],
        "recent_response_failures": [],
    }


def _evaluate_page(page: Page) -> dict[str, Any] | None:
    payload = _evaluate_probe_script(page)
    if payload is None:
        return None
    return {
        "readyState": payload.get("readyState", ""),
        "url": payload.get("url", ""),
        "title": payload.get("title", ""),
        "bodyExcerpt": payload.get("bodyExcerpt", ""),
        "hasComposer": payload.get("hasComposer", False),
        "hasSendButton": payload.get("hasSendButton", False),
        "hasNewChatButton": payload.get("hasNewChatButton", False),
        "hasLoginPrompt": payload.get("hasLoginPrompt", False),
        "hasHumanCheck": payload.get("hasHumanCheck", False),
        "assistantMessageCount": payload.get("assistantMessageCount", 0),
        "userMessageCount": payload.get("userMessageCount", 0),
    }


def _probe_transport_state(page: Page) -> dict[str, Any]:
    payload = _evaluate_probe_script(page)
    if payload is None:
        return _empty_transport_state()
    return {
        "page_url": str(payload.get("url", "")),
        "page_title": str(payload.get("title", "")),
        "body_excerpt": str(payload.get("bodyExcerpt", "")),
        "has_composer": bool(payload.get("hasComposer")),
        "composer_text": str(payload.get("composerText", "")),
        "has_send_button": bool(payload.get("hasSendButton")),
        "has_voice_input_button": bool(payload.get("hasVoiceInputButton")),
        "has_stop_button": bool(payload.get("hasStopButton")),
        "has_new_chat_button": bool(payload.get("hasNewChatButton")),
        "has_login_prompt": bool(payload.get("hasLoginPrompt")),
        "has_human_check": bool(payload.get("hasHumanCheck")),
        "assistant_message_count": int(payload.get("assistantMessageCount", 0)),
        "user_message_count": int(payload.get("userMessageCount", 0)),
        "assistant_busy_count": int(payload.get("assistantBusyCount", 0)),
        "is_streaming": bool(payload.get("isStreaming")),
        "last_assistant_text": str(payload.get("lastAssistantText", "")),
        "last_assistant_text_length": int(payload.get("lastAssistantTextLength", 0)),
        "assistant_messages": list(payload.get("assistantMessages", [])),
        "last_user_text": str(payload.get("lastUserText", "")),
        "last_user_text_length": int(payload.get("lastUserTextLength", 0)),
        "user_messages": list(payload.get("userMessages", [])),
        "controls": list(payload.get("controls", [])),
        "recent_response_failures": [],
    }


def _evaluate_probe_script(page: Page) -> dict[str, Any] | None:
    try:
        payload = page.evaluate(_PROBE_PAGE_SCRIPT)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _build_transport_failure_message(state: dict[str, Any]) -> str:
    if state.get("no_sandbox_detected"):
        return (
            "ChatGPT transport failed because Chrome is running with '--no-sandbox', "
            "which violates the manual attach contract."
        )
    if state.get("has_voice_input_button") and not state.get("has_send_button"):
        return (
            "ChatGPT composer exposed voice or microphone controls without an exact "
            "send button, so the runner refused to click an ambiguous control."
        )
    if state.get("has_login_prompt"):
        return "ChatGPT transport hit a login prompt before a reply arrived."
    if state.get("has_human_check"):
        return "ChatGPT transport stayed blocked by a challenge page before a reply arrived."
    failures = list(state.get("recent_response_failures", []))
    if failures:
        latest = failures[-1]
        status = int(latest.get("status", 0))
        url = str(latest.get("url", ""))
        return f"ChatGPT transport hit backend failure {status} at {url}."
    if _assistant_text_looks_like_user_echo(state):
        return (
            "ChatGPT transport only observed the user's prompt echoed in the "
            "assistant slot and never captured a distinct assistant reply."
        )
    if state.get("last_assistant_text"):
        return (
            "ChatGPT transport timed out before the assistant response finished streaming."
        )
    return "ChatGPT transport did not produce a usable assistant response."


def _normalize_message_excerpt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _assistant_text_looks_like_user_echo(state: dict[str, Any]) -> bool:
    raw_assistant_text = str(state.get("last_assistant_text", "") or "").strip()
    raw_user_text = str(state.get("last_user_text", "") or "").strip()
    assistant_text = _normalize_message_excerpt(raw_assistant_text)
    user_text = _normalize_message_excerpt(raw_user_text)
    if not assistant_text or not user_text:
        return False
    if len(assistant_text) < 20:
        return False
    if assistant_text == user_text:
        return True
    if assistant_text in user_text and not _looks_like_yamlish_reply(raw_assistant_text):
        return True
    if not _looks_like_yamlish_reply(raw_assistant_text):
        return False
    assistant_candidate = normalize_yaml_candidate(raw_assistant_text)
    if assistant_candidate:
        user_candidate = normalize_yaml_candidate(raw_user_text)
        if user_candidate:
            assistant_candidate_excerpt = _normalize_message_excerpt(assistant_candidate)
            user_candidate_excerpt = _normalize_message_excerpt(user_candidate)
            if assistant_candidate_excerpt == user_candidate_excerpt:
                return False
            candidate_prefix = assistant_candidate_excerpt[
                : min(len(assistant_candidate_excerpt), 220)
            ]
            if (
                len(assistant_candidate_excerpt) >= 200
                and len(assistant_candidate_excerpt) < len(user_candidate_excerpt)
                and candidate_prefix in user_candidate_excerpt
            ):
                return True
        return False
    return _yamlish_reply_matches_user_prompt_prefix(raw_assistant_text, raw_user_text)


def _assistant_reply_ready_for_return(
    state: dict[str, Any],
    *,
    expected_manifest: dict[str, Any] | None = None,
) -> bool:
    text = str(state.get("last_assistant_text", "") or "").strip()
    return _assistant_text_ready_for_return(
        text,
        expected_manifest=expected_manifest,
    )


def _assistant_text_ready_for_return(
    text: str,
    *,
    expected_manifest: dict[str, Any] | None = None,
) -> bool:
    text = str(text or "").strip()
    if not text:
        return False
    if not _looks_like_yamlish_reply(text):
        return True
    candidate = normalize_yaml_candidate(text)
    if not candidate:
        return False
    if expected_manifest:
        manifest_guard = validate_yaml_candidate_against_manifest(
            candidate,
            manifest=expected_manifest,
        )
        if not bool(manifest_guard.get("ok")):
            return False
    return True


def _transport_submission_started(state: dict[str, Any]) -> bool:
    if bool(state.get("is_streaming")):
        return True
    if bool(state.get("has_stop_button")):
        return True
    if int(state.get("assistant_busy_count", 0) or 0) > 0:
        return True
    if int(state.get("user_message_count", 0) or 0) > 0:
        return True
    return False


def _summarize_console_events(events: list[dict[str, Any]] | deque[dict[str, Any]]) -> list[str]:
    summaries: list[str] = []
    for item in list(events)[-12:]:
        event_type = str(item.get("type", "log")).upper()
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        if event_type == "LOG" and not any(
            marker in text.lower()
            for marker in (*CONSOLE_CHALLENGE_MARKERS, *CONSOLE_LOGIN_MARKERS)
        ):
            continue
        summaries.append(f"[{event_type}] {text}")
    return summaries[-8:]


def _detect_no_sandbox(processes: list[dict[str, Any]]) -> bool:
    return any(
        "--no-sandbox" in str(process.get("CommandLine", ""))
        for process in processes
    )


def _select_browser_pid(processes: list[dict[str, Any]]) -> int | None:
    root_processes = [
        process
        for process in processes
        if "--type=" not in str(process.get("CommandLine", ""))
    ]
    if not root_processes:
        return None
    port_marker = f"--remote-debugging-port={MANUAL_CDP_PORT}"
    for process in root_processes:
        if port_marker in str(process.get("CommandLine", "")):
            try:
                return int(process["ProcessId"])
            except Exception:
                return None
    try:
        return int(root_processes[0]["ProcessId"])
    except Exception:
        return None


def _build_attach_error_message(
    *,
    session: str,
    profile_dir: Path,
    endpoint: str,
    processes: list[dict[str, Any]],
    error: str,
) -> str:
    if not processes:
        return (
            f"ChatGPT browser session '{session}' is not open yet. Start Chrome manually "
            f"from a terminal with profile '{profile_dir}' and '--remote-debugging-port={MANUAL_CDP_PORT}', "
            "log in to ChatGPT, open one real conversation, keep that Chrome window open, "
            "then rerun -SessionCheckOnly."
        )
    port_marker = f"--remote-debugging-port={MANUAL_CDP_PORT}"
    if not any(port_marker in str(process.get("CommandLine", "")) for process in processes):
        return (
            f"ChatGPT browser session '{session}' is using the canonical profile, but Chrome is not "
            f"listening on {endpoint}. Restart that Chrome window manually with '--remote-debugging-port={MANUAL_CDP_PORT}', "
            "keep it open, finish login/challenge, open one real conversation, then rerun -SessionCheckOnly."
        )
    return (
        f"ChatGPT browser session '{session}' could not be attached at {endpoint}. "
        "Keep the manually opened Chrome window running and retry after ChatGPT finishes loading. "
        f"Underlying error: {error}"
    )


def _button_meta_text(meta: dict[str, Any]) -> str:
    return " ".join(
        str(meta.get(key, "") or "").strip()
        for key in ("text", "aria", "testid", "class_name")
    ).strip()


def _button_meta_is_voice_input(meta: dict[str, Any]) -> bool:
    if bool(meta.get("disabled")):
        return False
    testid = str(meta.get("testid", "") or "").strip().lower()
    if testid in {"send-button", "stop-button"}:
        return False
    return bool(VOICE_CONTROL_PATTERN.search(_button_meta_text(meta)))


def _button_meta_is_exact_send(meta: dict[str, Any]) -> bool:
    if bool(meta.get("disabled")):
        return False
    testid = str(meta.get("testid", "") or "").strip().lower()
    return testid == "send-button" and not _button_meta_is_voice_input(meta)


def _list_profile_processes(profile_dir: Path) -> list[dict[str, Any]]:
    script = f"""
$profile = @'{str(profile_dir)}'@
$escaped = [regex]::Escape($profile)
$rows = Get-CimInstance Win32_Process |
  Where-Object {{
    $_.CommandLine -and $_.CommandLine -match $escaped
  }} |
  Select-Object ProcessId, Name, CommandLine
if (-not $rows) {{
  "[]"
  exit 0
}}
$rows | ConvertTo-Json -Compress -Depth 3
"""
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return []
    output = completed.stdout.strip()
    if not output:
        return []
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    if "?" in value:
        value = value.split("?", 1)[0]
    if "#" in value:
        value = value.split("#", 1)[0]
    return value.rstrip("/")


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_page_url(page: Page) -> str:
    try:
        return page.url
    except Exception:
        return ""


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _looks_like_yamlish_reply(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    return any(
        marker in lowered
        for marker in (
            "report_content:",
            "title_slide:",
            "contents_slide:",
            "pattern_id:",
            "slots:",
            "slides:",
        )
    )


def _assistant_reply_has_parseable_yaml(text: str) -> bool:
    if not _looks_like_yamlish_reply(text):
        return False
    return bool(
        coerce_manual_ai_yaml_candidate(
            text,
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        ).normalized_yaml
    )


def _yamlish_reply_matches_user_prompt_prefix(assistant_text: str, user_text: str) -> bool:
    assistant_excerpt = _normalize_message_excerpt(assistant_text)
    user_excerpt = _normalize_message_excerpt(user_text)
    marker_count = sum(
        1
        for marker in (
            "report_content:",
            "title_slide:",
            "contents_slide:",
            "slides:",
            "pattern_id:",
            "detail_body:",
        )
        if marker in assistant_excerpt
    )
    if len(assistant_excerpt) < 300 or marker_count < 4 or not user_excerpt:
        return False
    prefix = assistant_excerpt[: min(len(assistant_excerpt), 240)]
    return prefix in user_excerpt


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
