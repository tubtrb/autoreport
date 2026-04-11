from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error
from urllib import parse, request

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_SESSION = "extai-chatgpt-spot"
DEFAULT_CHECKER_URL = "http://127.0.0.1:8000/api/manual-draft-check"
PLAYWRIGHT_CMD = [
    "npx.cmd",
    "--yes",
    "--package",
    "@playwright/cli",
    "playwright-cli",
]


@dataclass
class PromptSample:
    prompt_id: str
    label: str
    strength: str
    prompt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect repeated ChatGPT manual-YAML samples, rerun the local "
            "manual draft checker, and write artifact folders plus summaries."
        )
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION,
        help="Existing Playwright CLI browser session name.",
    )
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of fresh-chat samples to collect.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Artifact directory to create under output/playwright/ or elsewhere.",
    )
    parser.add_argument(
        "--prompt-pack",
        required=True,
        help="Path to a JSON prompt pack.",
    )
    parser.add_argument(
        "--checker-url",
        default=DEFAULT_CHECKER_URL,
        help="Local manual draft checker endpoint.",
    )
    parser.add_argument(
        "--checker-mode",
        choices=("http", "local"),
        default="http",
        help="Use the HTTP endpoint or the in-process checker logic from autoreport/web/app.py.",
    )
    parser.add_argument(
        "--send-wait-seconds",
        type=float,
        default=0.8,
        help="Delay after typing before clicking send.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=3.0,
        help="Polling interval while waiting for a response.",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=20,
        help="Maximum response polls per sample.",
    )
    return parser.parse_args()


def load_prompt_pack(path: Path) -> list[PromptSample]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples: list[PromptSample] = []
    for item in raw:
        samples.append(
            PromptSample(
                prompt_id=str(item["prompt_id"]),
                label=str(item["label"]),
                strength=str(item["strength"]),
                prompt=str(item["prompt"]),
            )
        )
    if not samples:
        raise RuntimeError("Prompt pack is empty.")
    return samples


def run_playwright(
    *,
    session: str,
    args: list[str],
    raw: bool = False,
    timeout: float = 60.0,
) -> str:
    command = [*PLAYWRIGHT_CMD, "--session", session]
    if raw:
        command.append("--raw")
    command.extend(args)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Playwright command failed: "
            + " ".join(command)
            + "\n"
            + (completed.stderr or "").strip()
        )
    return (completed.stdout or "").strip()


def run_playwright_code(
    *,
    session: str,
    code: str,
    timeout: float = 60.0,
) -> str:
    temp_dir = REPO_ROOT / ".playwright-cli"
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(
        prefix="playwright-code-",
        suffix=".js",
        dir=temp_dir,
    )
    try:
        Path(temp_path).write_text(code, encoding="utf-8")
    finally:
        os.close(file_descriptor)
    try:
        return run_playwright(
            session=session,
            args=["run-code", "--filename", temp_path],
            timeout=timeout,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)


def raw_eval(session: str, expression: str, *, timeout: float = 30.0) -> Any:
    output = run_playwright(
        session=session,
        args=["eval", expression],
        raw=True,
        timeout=timeout,
    )
    if not output:
        return ""
    return json.loads(output)


def click_new_chat(session: str) -> str:
    return str(
        raw_eval(
            session,
            (
                "(function(){"
                "const button = Array.from(document.querySelectorAll('[data-testid]'))"
                ".find(node => ((node.getAttribute('data-testid') || '') === "
                "'create-new-chat-button'));"
                "if (button) { button.click(); return 'clicked'; }"
                "return 'missing';"
                "})()"
            ),
        )
    )


def click_composer(session: str) -> str:
    return str(
        raw_eval(
            session,
            (
                "(function(){"
                "const box = document.querySelector('[contenteditable=true]');"
                "if (box) { box.click(); box.focus(); return 'clicked'; }"
                "return 'missing';"
                "})()"
            ),
        )
    )


def click_send_button(session: str) -> str:
    return str(
        raw_eval(
            session,
            (
                "(function(){"
                "const button = Array.from(document.querySelectorAll('[data-testid]'))"
                ".find(node => ((node.getAttribute('data-testid') || '') === "
                "'send-button'));"
                "if (button) { button.click(); return 'clicked'; }"
                "return 'missing';"
                "})()"
            ),
        )
    )


def get_composer_text(session: str) -> str:
    values = raw_eval(
        session,
        (
            "JSON.stringify(Array.from(document.querySelectorAll('[contenteditable]'))"
            ".map(node => node.innerText))"
        ),
    )
    if isinstance(values, str):
        parsed = json.loads(values)
        return str(parsed[0]) if parsed else ""
    if isinstance(values, list):
        return str(values[0]) if values else ""
    return str(values)


def clear_and_type_prompt(session: str, prompt: str) -> None:
    if click_composer(session) != "clicked":
        raise RuntimeError("Could not focus the ChatGPT composer.")
    normalized_prompt = prompt.replace("\r\n", "\n").replace("\r", "\n")
    prompt_b64 = base64.b64encode(normalized_prompt.encode("utf-8")).decode("ascii")
    insertion_result = raw_eval(
        session,
        (
            "(function(){"
            "const box = document.querySelector('[contenteditable=true]');"
            "if (!box) return {ok:false, reason:'missing'};"
            f"const encoded = '{prompt_b64}';"
            "const bytes = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));"
            "const text = new TextDecoder().decode(bytes);"
            "box.focus();"
            "box.innerHTML = '';"
            "for (const line of text.split('\\n')) {"
            "  const paragraph = document.createElement('p');"
            "  if (line) {"
            "    paragraph.textContent = line;"
            "  } else {"
            "    paragraph.appendChild(document.createElement('br'));"
            "  }"
            "  box.appendChild(paragraph);"
            "}"
            "box.dispatchEvent(new InputEvent('input', {"
            "  bubbles: true,"
            "  inputType: 'insertText',"
            "  data: text"
            "}));"
            "return {ok:true, innerText: box.innerText, html: box.innerHTML};"
            "})()"
        ),
        timeout=30.0,
    )
    if not isinstance(insertion_result, dict) or not insertion_result.get("ok"):
        raise RuntimeError("Prompt insertion failed inside the ChatGPT composer.")
    time.sleep(0.4)
    composer_text = get_composer_text(session)
    if not composer_text.strip():
        raise RuntimeError("Prompt insertion failed; composer text is empty.")
    first_line = normalized_prompt.splitlines()[0].strip()
    last_line = normalized_prompt.splitlines()[-1].strip()
    if first_line and first_line not in composer_text:
        raise RuntimeError("Prompt insertion failed; first line is missing from the composer.")
    if last_line and last_line not in composer_text:
        raise RuntimeError("Prompt insertion failed; last line is missing from the composer.")


def get_turn_count(session: str) -> int:
    return int(
        raw_eval(
            session,
            (
                "(function(){"
                "return Array.from(document.querySelectorAll('[data-testid]'))"
                ".filter(node => ((node.getAttribute('data-testid') || '')"
                ".startsWith('conversation-turn-'))).length;"
                "})()"
            ),
        )
    )


def get_last_turn_text(session: str) -> str:
    return str(
        raw_eval(
            session,
            (
                "(function(){"
                "const turns = Array.from(document.querySelectorAll('[data-testid]'))"
                ".filter(node => ((node.getAttribute('data-testid') || '')"
                ".startsWith('conversation-turn-')));"
                "return turns.length ? turns[turns.length - 1].innerText : '';"
                "})()"
            ),
            timeout=40.0,
        )
    )


def normalize_yaml_candidate(raw_turn_text: str) -> str:
    candidate = raw_turn_text.strip()
    candidate = re.sub(r"^\s*(ChatGPT의 말:|ChatGPT said:)\s*", "", candidate)
    candidate = re.sub(r"^\s*YAML\s*", "", candidate)
    report_content_match = re.search(r"report_content:", candidate, re.IGNORECASE)
    if report_content_match:
        candidate = candidate[report_content_match.start() :]
    lines = candidate.splitlines()
    while lines:
        line = lines[-1].rstrip()
        if not line:
            lines.pop()
            continue
        if (
            line.startswith(" ")
            or line.startswith("-")
            or line.startswith("#")
            or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", line)
        ):
            break
        lines.pop()
    return "\n".join(lines).strip()


def post_checker(checker_url: str, yaml_candidate: str) -> dict[str, Any]:
    data = parse.urlencode(
        {
            "payload_yaml": yaml_candidate,
            "built_in": "autoreport_manual",
        }
    ).encode("utf-8")
    req = request.Request(
        checker_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            payload["_http_status"] = response.status
            return payload
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {
                "ok": False,
                "message": f"Checker HTTP {exc.code}: {body}",
                "errors": [],
                "warnings": [],
                "summary": {},
            }
        payload["_http_status"] = exc.code
        return payload
    except Exception as exc:  # pragma: no cover - operational fallback
        return {
            "ok": False,
            "message": f"Checker request failed: {exc}",
            "errors": [],
            "warnings": [],
            "summary": {},
            "_http_status": 0,
        }


def run_checker_local(yaml_candidate: str) -> dict[str, Any]:
    import yaml

    from autoreport.loader import parse_yaml_text
    from autoreport.web.app import (
        MANUAL_PUBLIC_TEMPLATE_NAME,
        _build_manual_draft_check,
    )

    try:
        raw_data = parse_yaml_text(yaml_candidate)
    except yaml.YAMLError as exc:
        return {
            "error_type": "yaml_parse_error",
            "message": f"Failed to parse YAML: {exc}",
            "_http_status": 400,
        }
    return {
        **_build_manual_draft_check(raw_data, built_in=MANUAL_PUBLIC_TEMPLATE_NAME),
        "_http_status": 200,
    }


def classify_result(checker_payload: dict[str, Any]) -> str:
    message = str(checker_payload.get("message", ""))
    errors = [str(item) for item in checker_payload.get("errors", [])]
    warnings = [str(item) for item in checker_payload.get("warnings", [])]
    summary = checker_payload.get("summary", {}) or {}
    payload_kind = str(summary.get("payload_kind", ""))

    if "Failed to parse YAML" in message:
        return "yaml-parse-failure"
    if message.startswith("Checker request failed:"):
        return "checker-failure"
    if any(
        "The draft must be a YAML mapping rooted at report_content." in error
        for error in errors
    ):
        return "no-yaml-response"
    if payload_kind and payload_kind != "content":
        return "wrong-payload-kind"
    if any(
        token in error
        for error in errors
        for token in (
            "Field 'title_slide' is required.",
            "Field 'title_slide.slots' must be an object.",
            "Field 'contents_slide.slots' must be an object.",
            "Field 'slides' must contain at least 1 item.",
        )
    ):
        return "manual-structure-drift"
    if any("pattern_id" in error for error in errors):
        return "pattern-rule-failure"
    if warnings:
        return "warning-only"
    if checker_payload.get("ok") and payload_kind == "content":
        return "manual-pass"
    return "unknown"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def collect_sample(
    *,
    index: int,
    sample: PromptSample,
    session: str,
    checker_url: str,
    checker_mode: str,
    output_dir: Path,
    send_wait_seconds: float,
    poll_seconds: float,
    max_polls: int,
) -> dict[str, Any]:
    sample_dir = output_dir / f"{index:03d}-{sample.prompt_id}"
    sample_dir.mkdir(parents=True, exist_ok=True)
    write_text(sample_dir / "prompt.txt", sample.prompt)

    page_url_before = str(raw_eval(session, "document.location.href"))
    page_title_before = str(raw_eval(session, "document.title"))
    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")

    if click_new_chat(session) != "clicked":
        raise RuntimeError("Could not click the ChatGPT new-chat button.")
    time.sleep(2.0)
    clear_and_type_prompt(session, sample.prompt)
    time.sleep(send_wait_seconds)
    if click_send_button(session) != "clicked":
        raise RuntimeError("Could not click the ChatGPT send button.")

    stable_hits = 0
    previous_turn = ""
    last_turn = ""
    last_turn_count = 0
    for _ in range(max_polls):
        time.sleep(poll_seconds)
        last_turn_count = get_turn_count(session)
        current_turn = get_last_turn_text(session)
        if last_turn_count >= 2 and len(current_turn.strip()) > 40:
            stable_hits = stable_hits + 1 if current_turn == previous_turn else 0
            previous_turn = current_turn
            last_turn = current_turn
            if stable_hits >= 1:
                break
    if not last_turn.strip():
        raise RuntimeError("No assistant response was captured from ChatGPT.")

    yaml_candidate = normalize_yaml_candidate(last_turn)
    checker_payload = (
        run_checker_local(yaml_candidate)
        if checker_mode == "local"
        else post_checker(checker_url, yaml_candidate)
    )
    category = classify_result(checker_payload)
    page_url_after = str(raw_eval(session, "document.location.href"))
    page_title_after = str(raw_eval(session, "document.title"))

    write_text(sample_dir / "raw-turn.txt", last_turn)
    write_text(sample_dir / "yaml-candidate.yaml", yaml_candidate)
    write_text(
        sample_dir / "checker.json",
        json.dumps(checker_payload, ensure_ascii=False, indent=2),
    )
    write_text(
        sample_dir / "metadata.json",
        json.dumps(
            {
                "index": index,
                "prompt_id": sample.prompt_id,
                "label": sample.label,
                "strength": sample.strength,
                "collected_at": collected_at,
                "page_url_before": page_url_before,
                "page_title_before": page_title_before,
                "page_url_after": page_url_after,
                "page_title_after": page_title_after,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    summary = checker_payload.get("summary", {}) or {}
    errors = [str(item) for item in checker_payload.get("errors", [])]
    warnings = [str(item) for item in checker_payload.get("warnings", [])]
    return {
        "index": index,
        "prompt_id": sample.prompt_id,
        "label": sample.label,
        "strength": sample.strength,
        "category": category,
        "ok": bool(checker_payload.get("ok", False)),
        "payload_kind": summary.get("payload_kind", ""),
        "blocking_issue_count": summary.get("blocking_issue_count", 0),
        "warning_count": summary.get("warning_count", 0),
        "message": checker_payload.get("message", ""),
        "first_error": errors[0] if errors else "",
        "first_warning": warnings[0] if warnings else "",
        "sample_dir": str(sample_dir),
    }


def write_summary(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    write_text(
        output_dir / "summary.json",
        json.dumps(rows, ensure_ascii=False, indent=2),
    )

    csv_path = output_dir / "summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "prompt_id",
                "label",
                "strength",
                "category",
                "ok",
                "payload_kind",
                "blocking_issue_count",
                "warning_count",
                "message",
                "first_error",
                "first_warning",
                "sample_dir",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["category"] for row in rows)
    lines = [
        "ChatGPT Corpus Summary",
        f"Collected samples: {len(rows)}",
        "",
        "Category counts:",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("Per-sample results:")
    for row in rows:
        lines.append(
            f"- #{row['index']:03d} {row['prompt_id']} {row['label']}: "
            f"{row['category']} | blocking={row['blocking_issue_count']} "
            f"| warnings={row['warning_count']}"
        )
        if row["first_error"]:
            lines.append(f"  first_error: {row['first_error']}")
        elif row["first_warning"]:
            lines.append(f"  first_warning: {row['first_warning']}")
    write_text(output_dir / "summary.txt", "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    prompt_pack_path = Path(args.prompt_pack).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_pack = load_prompt_pack(prompt_pack_path)
    metadata = {
        "session": args.session,
        "count": args.count,
        "checker_url": args.checker_url,
        "prompt_pack": str(prompt_pack_path),
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_text(
        output_dir / "run-metadata.json",
        json.dumps(metadata, ensure_ascii=False, indent=2),
    )

    rows: list[dict[str, Any]] = []
    for index in range(1, args.count + 1):
        sample = prompt_pack[(index - 1) % len(prompt_pack)]
        print(f"[{index}/{args.count}] {sample.prompt_id} {sample.label}", flush=True)
        try:
            row = collect_sample(
                index=index,
                sample=sample,
                session=args.session,
                checker_url=args.checker_url,
                checker_mode=args.checker_mode,
                output_dir=output_dir,
                send_wait_seconds=args.send_wait_seconds,
                poll_seconds=args.poll_seconds,
                max_polls=args.max_polls,
            )
        except Exception as exc:  # pragma: no cover - operational path
            failure_dir = output_dir / f"{index:03d}-{sample.prompt_id}"
            failure_dir.mkdir(parents=True, exist_ok=True)
            write_text(failure_dir / "prompt.txt", sample.prompt)
            write_text(failure_dir / "failure.txt", str(exc))
            row = {
                "index": index,
                "prompt_id": sample.prompt_id,
                "label": sample.label,
                "strength": sample.strength,
                "category": "collection-failure",
                "ok": False,
                "payload_kind": "",
                "blocking_issue_count": -1,
                "warning_count": 0,
                "message": "Sample collection failed.",
                "first_error": str(exc),
                "first_warning": "",
                "sample_dir": str(failure_dir),
            }
        rows.append(row)
        print(
            json.dumps(
                {
                    "index": row["index"],
                    "prompt_id": row["prompt_id"],
                    "label": row["label"],
                    "category": row["category"],
                    "blocking_issue_count": row["blocking_issue_count"],
                    "first_error": row["first_error"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    write_summary(output_dir, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
