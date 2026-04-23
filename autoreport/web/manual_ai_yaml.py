from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

import yaml

from autoreport.loader import parse_yaml_text
from autoreport.web.style_presets import MANUAL_PUBLIC_TEMPLATE_NAME


_MANUAL_AI_KEY_RE = re.compile(
    r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:(?:\s*(?P<value>.*))?$"
)
_MANUAL_AI_SLIDE_PATTERN_RE = re.compile(r"^-\s*pattern_id\s*:\s*.+$")
_MANUAL_AI_BLOCK_SCALAR_RE = re.compile(r":\s*[>|][+-]?\s*$")
_MANUAL_AI_IMAGE_ALIAS_RE = re.compile(r"^(?:image|caption)_[1-9]\d*$")
_MANUAL_AI_ROOT_CHILD_KEYS = {"title_slide", "contents_slide", "slides"}
_MANUAL_AI_TITLE_SLOT_KEYS = {
    "doc_title",
    "doc_subtitle",
    "doc_version",
    "author_or_owner",
}
_MANUAL_AI_CONTENTS_SLOT_KEYS = {
    "contents_title",
    "contents_group_label",
}
_MANUAL_AI_SLIDE_SLOT_KEYS = {
    "section_no",
    "section_title",
    "section_subtitle",
    "step_no",
    "step_title",
    "command_or_action",
    "summary",
    "detail_body",
}
_FENCED_BLOCK_RE = re.compile(r"```(?:yaml|yml)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_VISIBLE_LABEL_RE = re.compile(r"^(?:chatgpt(?:\s+said)?|yaml)\s*:?\s*$", re.IGNORECASE)

_EXTRACTION_ACTIONS = frozenset(
    {
        "stripped_visible_label",
        "extracted_fenced_yaml",
        "trimmed_leading_prose",
        "trimmed_trailing_prose",
    }
)

MANUAL_AI_AUTO_REPAIR_WARNING = (
    "Auto-corrected common manual YAML indentation drift before checking."
)
MANUAL_AI_AUTO_REPAIR_HINT = (
    "The draft was re-indented automatically. Review the repaired YAML in the editor before generating."
)
MANUAL_AI_TRAILING_QUOTE_WARNING = (
    "Closed a truncated trailing quoted YAML scalar before checking."
)
MANUAL_AI_TRAILING_QUOTE_HINT = (
    "The draft appeared to end inside a quoted YAML value. Review the recovered YAML in the editor before generating."
)
MANUAL_AI_EXTRACTION_WARNING = (
    "Recovered the manual YAML block from surrounding prose before checking."
)
MANUAL_AI_EXTRACTION_HINT = (
    "The draft included extra prose or code fences. Review the extracted YAML in the editor before generating."
)
MANUAL_AI_ROOT_WRAP_WARNING = (
    "Wrapped a rootless manual YAML snippet under report_content before checking."
)
MANUAL_AI_ROOT_WRAP_HINT = (
    "The draft omitted the report_content root. Review the wrapped YAML in the editor before generating."
)


@dataclass(frozen=True)
class ManualAiYamlCoercionResult:
    normalized_yaml: str | None
    actions: tuple[str, ...] = ()
    failure_reason: str = ""

    @property
    def coercion_applied(self) -> bool:
        return bool(self.actions)


def is_manual_public_template(built_in: str) -> bool:
    return built_in == MANUAL_PUBLIC_TEMPLATE_NAME


def parse_public_payload_yaml(
    payload_yaml: str,
    *,
    built_in: str,
) -> tuple[object, ManualAiYamlCoercionResult | None]:
    original_data: object | None = None
    original_exc: yaml.YAMLError | None = None

    try:
        original_data = parse_yaml_text(payload_yaml)
    except yaml.YAMLError as exc:
        original_exc = exc

    if is_manual_public_template(built_in):
        coercion = coerce_manual_ai_yaml_candidate(payload_yaml, built_in=built_in)
        if coercion.normalized_yaml is not None:
            parsed = parse_yaml_text(coercion.normalized_yaml)
            if coercion.coercion_applied:
                return parsed, coercion
            if original_exc is None:
                return parsed, None
        if original_exc is not None:
            raise original_exc
        if original_data is None:
            raise yaml.YAMLError("Empty YAML document.")
        return original_data, None

    if original_exc is not None:
        raise original_exc
    if original_data is None:
        raise yaml.YAMLError("Empty YAML document.")
    return original_data, None


def coerce_manual_ai_yaml_candidate(
    payload_yaml: str,
    *,
    built_in: str,
) -> ManualAiYamlCoercionResult:
    if not is_manual_public_template(built_in):
        return ManualAiYamlCoercionResult(normalized_yaml=None, failure_reason="unsupported_template")

    actions: list[str] = []
    candidate = _normalize_newlines(payload_yaml).strip()
    if not candidate:
        return ManualAiYamlCoercionResult(normalized_yaml=None, failure_reason="empty")

    fenced_candidate = _extract_preferred_fenced_yaml(candidate)
    if fenced_candidate is not None:
        candidate = fenced_candidate
        _append_action(actions, "extracted_fenced_yaml")

    lines = candidate.splitlines()
    if not lines:
        return ManualAiYamlCoercionResult(normalized_yaml=None, failure_reason="empty")

    label_trimmed = False
    while lines and _VISIBLE_LABEL_RE.fullmatch(lines[0].strip()):
        lines.pop(0)
        label_trimmed = True
    if label_trimmed:
        _append_action(actions, "stripped_visible_label")
    candidate = "\n".join(lines).strip()
    if not candidate:
        return ManualAiYamlCoercionResult(normalized_yaml=None, failure_reason="empty")

    lines = candidate.splitlines()
    start_index = _find_structural_start_index(lines)
    if start_index is not None:
        preserved_prefix = [
            line.rstrip()
            for line in lines[:start_index]
            if not line.strip() or line.lstrip().startswith("#")
        ]
        if start_index != len(preserved_prefix):
            _append_action(actions, "trimmed_leading_prose")
        lines = preserved_prefix + lines[start_index:]
    else:
        lines = [line.rstrip() for line in lines]

    trimmed_trailing = False
    while lines:
        last_line = lines[-1]
        if not last_line.strip():
            lines.pop()
            continue
        if _line_looks_like_yaml_tail(last_line):
            break
        lines.pop()
        trimmed_trailing = True
    if trimmed_trailing:
        _append_action(actions, "trimmed_trailing_prose")

    if not lines:
        return ManualAiYamlCoercionResult(normalized_yaml=None, failure_reason="empty")

    candidate = "\n".join(lines).strip()
    wrapped_candidate = _wrap_rootless_report_content(candidate)
    if wrapped_candidate is not None:
        candidate = wrapped_candidate
        _append_action(actions, "wrapped_report_content_root")

    try:
        parsed = parse_yaml_text(candidate)
    except yaml.YAMLError:
        repaired_candidate = _repair_manual_ai_yaml_indentation(
            candidate,
            built_in=built_in,
        )
        if repaired_candidate is not None and repaired_candidate != candidate:
            candidate = repaired_candidate
            _append_action(actions, "repaired_indentation")
            try:
                parsed = parse_yaml_text(candidate)
            except yaml.YAMLError:
                closed_quote_candidate = _close_trailing_quoted_scalar(candidate)
                if (
                    closed_quote_candidate is not None
                    and closed_quote_candidate != candidate
                ):
                    candidate = closed_quote_candidate
                    _append_action(actions, "closed_trailing_quote")
                    try:
                        parsed = parse_yaml_text(candidate)
                    except yaml.YAMLError:
                        return ManualAiYamlCoercionResult(
                            normalized_yaml=None,
                            actions=tuple(actions),
                            failure_reason="parse_failed",
                        )
                else:
                    return ManualAiYamlCoercionResult(
                        normalized_yaml=None,
                        actions=tuple(actions),
                        failure_reason="parse_failed",
                    )
        else:
            return ManualAiYamlCoercionResult(
                normalized_yaml=None,
                actions=tuple(actions),
                failure_reason="parse_failed",
            )

    if not _looks_like_manual_report_content_document(parsed):
        return ManualAiYamlCoercionResult(
            normalized_yaml=None,
            actions=tuple(actions),
            failure_reason="not_manual_report_content",
        )
    return ManualAiYamlCoercionResult(normalized_yaml=candidate, actions=tuple(actions))


def manual_ai_coercion_warnings(actions: Sequence[str]) -> list[str]:
    action_set = set(actions)
    warnings: list[str] = []
    if "repaired_indentation" in action_set:
        warnings.append(MANUAL_AI_AUTO_REPAIR_WARNING)
    if "closed_trailing_quote" in action_set:
        warnings.append(MANUAL_AI_TRAILING_QUOTE_WARNING)
    if action_set & _EXTRACTION_ACTIONS:
        warnings.append(MANUAL_AI_EXTRACTION_WARNING)
    if "wrapped_report_content_root" in action_set:
        warnings.append(MANUAL_AI_ROOT_WRAP_WARNING)
    return warnings


def manual_ai_coercion_hints(actions: Sequence[str]) -> list[str]:
    action_set = set(actions)
    hints: list[str] = []
    if "repaired_indentation" in action_set:
        hints.append(MANUAL_AI_AUTO_REPAIR_HINT)
    if "closed_trailing_quote" in action_set:
        hints.append(MANUAL_AI_TRAILING_QUOTE_HINT)
    if action_set & _EXTRACTION_ACTIONS:
        hints.append(MANUAL_AI_EXTRACTION_HINT)
    if "wrapped_report_content_root" in action_set:
        hints.append(MANUAL_AI_ROOT_WRAP_HINT)
    return hints


def append_manual_ai_coercion_feedback(
    response_payload: dict[str, object],
    *,
    coercion: ManualAiYamlCoercionResult,
) -> dict[str, object]:
    if coercion.normalized_yaml is None or not coercion.coercion_applied:
        return response_payload

    updated_payload = dict(response_payload)
    warnings = list(updated_payload.get("warnings", []))
    for warning in manual_ai_coercion_warnings(coercion.actions):
        if warning not in warnings:
            warnings.append(warning)
    hints = list(updated_payload.get("hints", []))
    for hint in manual_ai_coercion_hints(coercion.actions):
        if hint not in hints:
            hints.append(hint)
    summary = dict(updated_payload.get("summary", {}) or {})
    summary["warning_count"] = len(warnings)
    updated_payload["warnings"] = warnings
    updated_payload["hints"] = hints
    updated_payload["summary"] = summary
    updated_payload["payload_yaml"] = coercion.normalized_yaml
    if not updated_payload.get("errors"):
        updated_payload["message"] = _coercion_success_message(coercion.actions)
    return updated_payload


def _coercion_success_message(actions: Sequence[str]) -> str:
    if set(actions) == {"repaired_indentation"}:
        return (
            "Draft checker passed with warnings. Review the repaired indentation and rule hints before generating."
        )
    return (
        "Draft checker passed with warnings. Review the recovered YAML draft and rule hints before generating."
    )


def _looks_like_manual_report_content_document(raw_data: object) -> bool:
    if not isinstance(raw_data, dict):
        return False
    if isinstance(raw_data.get("report_content"), dict):
        return True
    return _is_rootless_report_content_mapping(raw_data)


def _is_rootless_report_content_mapping(raw_data: object) -> bool:
    if not isinstance(raw_data, dict) or "report_content" in raw_data:
        return False
    return any(key in raw_data for key in _MANUAL_AI_ROOT_CHILD_KEYS)


def _normalize_newlines(payload_yaml: str) -> str:
    return payload_yaml.replace("\r\n", "\n").replace("\r", "\n")


def _extract_preferred_fenced_yaml(candidate: str) -> str | None:
    blocks = [match.group(1).strip() for match in _FENCED_BLOCK_RE.finditer(candidate)]
    if not blocks:
        return None
    for block in blocks:
        if _contains_report_content_start(block):
            return block
    return blocks[0]


def _contains_report_content_start(candidate: str) -> bool:
    lines = candidate.splitlines()
    return _find_structural_start_index(lines) is not None


def _find_structural_start_index(lines: Sequence[str]) -> int | None:
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        if stripped_line == "report_content:":
            return index
        key_match = _MANUAL_AI_KEY_RE.match(stripped_line)
        if key_match is not None and key_match.group("key") in _MANUAL_AI_ROOT_CHILD_KEYS:
            return index
    return None


def _line_looks_like_yaml_tail(line: str) -> bool:
    stripped_line = line.strip()
    if not stripped_line or stripped_line.startswith("#"):
        return True
    if line[:1].isspace():
        return True
    return bool(
        stripped_line == "report_content:"
        or _MANUAL_AI_KEY_RE.match(stripped_line)
        or _MANUAL_AI_SLIDE_PATTERN_RE.match(stripped_line)
    )


def _wrap_rootless_report_content(candidate: str) -> str | None:
    lines = candidate.splitlines()
    start_index = _find_structural_start_index(lines)
    if start_index is None:
        return None
    first_structural = lines[start_index].strip()
    if first_structural == "report_content:":
        return None
    key_match = _MANUAL_AI_KEY_RE.match(first_structural)
    if key_match is None or key_match.group("key") not in _MANUAL_AI_ROOT_CHILD_KEYS:
        return None
    prefix = [line.rstrip() for line in lines[:start_index]]
    body = [line.rstrip() for line in lines[start_index:]]
    wrapped = prefix + ["report_content:"]
    wrapped.extend(f"  {line}" if line else "" for line in body)
    return "\n".join(wrapped).strip()


def _manual_ai_known_slot_key(key: str, *, context: str | None) -> bool:
    if context == "title_slide":
        return key in _MANUAL_AI_TITLE_SLOT_KEYS
    if context == "contents_slide":
        return key in _MANUAL_AI_CONTENTS_SLOT_KEYS
    if context == "slide":
        return key in _MANUAL_AI_SLIDE_SLOT_KEYS or bool(
            _MANUAL_AI_IMAGE_ALIAS_RE.fullmatch(key)
        )
    return False


def _manual_ai_block_terminator(stripped_line: str, *, context: str | None) -> bool:
    if stripped_line == "report_content:":
        return True
    key_match = _MANUAL_AI_KEY_RE.match(stripped_line)
    if key_match is not None:
        key = key_match.group("key")
        if key in _MANUAL_AI_ROOT_CHILD_KEYS or key in {"pattern_id", "slots"}:
            return True
        return _manual_ai_known_slot_key(key, context=context)
    return bool(_MANUAL_AI_SLIDE_PATTERN_RE.match(stripped_line))


def _repair_manual_ai_yaml_indentation(
    payload_yaml: str,
    *,
    built_in: str,
) -> str | None:
    if not is_manual_public_template(built_in):
        return None

    stripped = payload_yaml.strip()
    root_match = re.search(r"(?m)^\s*report_content:\s*$", stripped)
    if root_match is None:
        return None

    prefix = stripped[: root_match.start()]
    preserved_prefix_lines = [
        line.rstrip()
        for line in prefix.splitlines()
        if not line.strip() or line.lstrip().startswith("#")
    ]
    candidate_lines = stripped[root_match.start() :].splitlines()
    repaired_lines: list[str] = []
    section: str | None = None
    slot_context: str | None = None
    block_scalar_indent: int | None = None
    flow_scalar_indent: int | None = None
    line_index = 0

    while line_index < len(candidate_lines):
        raw_line = candidate_lines[line_index].rstrip()
        stripped_line = raw_line.strip()

        if not stripped_line:
            repaired_lines.append(
                "" if block_scalar_indent is None else " " * block_scalar_indent
            )
            flow_scalar_indent = None
            line_index += 1
            continue

        if stripped_line.startswith("```"):
            line_index += 1
            continue

        if block_scalar_indent is not None:
            if _manual_ai_block_terminator(stripped_line, context=slot_context):
                block_scalar_indent = None
                continue
            repaired_lines.append((" " * block_scalar_indent) + stripped_line)
            line_index += 1
            continue

        if flow_scalar_indent is not None:
            if _manual_ai_block_terminator(stripped_line, context=slot_context):
                flow_scalar_indent = None
                continue
            repaired_lines.append((" " * flow_scalar_indent) + stripped_line)
            line_index += 1
            continue

        if stripped_line.startswith("#"):
            repaired_lines.append(raw_line)
            flow_scalar_indent = None
            line_index += 1
            continue

        if stripped_line == "report_content:":
            repaired_lines.append("report_content:")
            section = None
            slot_context = None
            flow_scalar_indent = None
            line_index += 1
            continue

        key_match = _MANUAL_AI_KEY_RE.match(stripped_line)
        if key_match is not None:
            key = key_match.group("key")
            if key in _MANUAL_AI_ROOT_CHILD_KEYS:
                repaired_lines.append(f"  {key}:")
                section = key
                slot_context = None
                flow_scalar_indent = None
                line_index += 1
                continue

            if section in {"title_slide", "contents_slide"}:
                if key == "pattern_id":
                    repaired_lines.append(f"    {stripped_line}")
                    flow_scalar_indent = None
                    line_index += 1
                    continue
                if key == "slots":
                    repaired_lines.append("    slots:")
                    slot_context = section
                    flow_scalar_indent = None
                    line_index += 1
                    continue
                if _manual_ai_known_slot_key(key, context=slot_context):
                    repaired_lines.append(f"      {stripped_line}")
                    if _MANUAL_AI_BLOCK_SCALAR_RE.search(stripped_line):
                        block_scalar_indent = 8
                        flow_scalar_indent = None
                    elif key_match.group("value"):
                        flow_scalar_indent = 8
                    else:
                        flow_scalar_indent = None
                    line_index += 1
                    continue
                line_index += 1
                continue

            if section == "slides":
                if key == "slots":
                    repaired_lines.append("      slots:")
                    slot_context = "slide"
                    flow_scalar_indent = None
                    line_index += 1
                    continue
                if key == "pattern_id":
                    repaired_lines.append(f"    - {stripped_line}")
                    slot_context = "slide"
                    flow_scalar_indent = None
                    line_index += 1
                    continue
                if _manual_ai_known_slot_key(key, context=slot_context):
                    repaired_lines.append(f"        {stripped_line}")
                    if _MANUAL_AI_BLOCK_SCALAR_RE.search(stripped_line):
                        block_scalar_indent = 10
                        flow_scalar_indent = None
                    elif key_match.group("value"):
                        flow_scalar_indent = 10
                    else:
                        flow_scalar_indent = None
                    line_index += 1
                    continue
                line_index += 1
                continue

            line_index += 1
            continue

        if section == "slides" and _MANUAL_AI_SLIDE_PATTERN_RE.match(stripped_line):
            repaired_lines.append(f"    {stripped_line}")
            slot_context = "slide"
            flow_scalar_indent = None
            line_index += 1
            continue

        line_index += 1

    repaired_yaml = "\n".join(
        [*preserved_prefix_lines, *repaired_lines] if preserved_prefix_lines else repaired_lines
    ).strip()
    return repaired_yaml or None


def _append_action(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


def _close_trailing_quoted_scalar(candidate: str) -> str | None:
    lines = candidate.splitlines()
    last_index: int | None = None
    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            last_index = index
            break
    if last_index is None:
        return None
    line = lines[last_index].rstrip()
    if ":" not in line:
        return None
    if _has_unbalanced_single_quote(line):
        lines[last_index] = f"{line}'"
        return "\n".join(lines).strip()
    if _has_unbalanced_double_quote(line):
        lines[last_index] = f'{line}"'
        return "\n".join(lines).strip()
    return None


def _has_unbalanced_single_quote(line: str) -> bool:
    quote_count = 0
    index = 0
    while index < len(line):
        if line[index] != "'":
            index += 1
            continue
        if index + 1 < len(line) and line[index + 1] == "'":
            index += 2
            continue
        quote_count += 1
        index += 1
    return quote_count % 2 == 1


def _has_unbalanced_double_quote(line: str) -> bool:
    quote_count = 0
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quote_count += 1
    return quote_count % 2 == 1
