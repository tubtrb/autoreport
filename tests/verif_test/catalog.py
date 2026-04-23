from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from autoreport.loader import parse_yaml_text
from autoreport.templates.manual_procedure_variants import (
    MANUAL_ALLOWED_BODY_PATTERN_IDS,
    MANUAL_PROCEDURE_PATTERN_IDS_BY_IMAGE_COUNT,
    MANUAL_PROCEDURE_VARIANTS,
)
from autoreport.web.app import MANUAL_DRAFT_PROMPT_FOOTER, MANUAL_DRAFT_PROMPT_HEADER


REPO_ROOT = Path(__file__).resolve().parents[2]
CASE_CATALOG_PATH = Path(__file__).resolve().parent / "cases" / "manual_public_cases.yaml"
REVIEW_CASE_IDS = frozenset(
    {
        "01_one_image_canary",
        "05_balanced_canary",
        "10_full_family_canary",
    }
)
DEFAULT_SUITE_NAME = "full"
_PATTERN_IMAGE_COUNTS = {
    pattern_id: image_count
    for image_count, pattern_ids in MANUAL_PROCEDURE_PATTERN_IDS_BY_IMAGE_COUNT.items()
    for pattern_id in pattern_ids
}
_ONE_IMAGE_LABELS = {
    str(variant["pattern_id"]): str(variant["label"])
    for variant in MANUAL_PROCEDURE_VARIANTS
}
_TEXT_DENSITY_PARAGRAPHS = {
    "concise": (
        "Confirm the visible state and capture the required screenshot before moving on.",
        "Keep the screenshot note short and tied to the visible result.",
    ),
    "balanced": (
        "State the operator action, the visible UI change, and the expected result in order.",
        "Keep each screenshot note tied to the step number and the proof check.",
    ),
    "dense": (
        "Describe the operator action precisely and name the visible screen region.",
        "State the expected result and the comparison point the reviewer should check.",
        "End with the completion cue that must appear before the next step starts.",
    ),
}


@dataclass(frozen=True)
class ManualPublicCase:
    case_id: str
    label: str
    body_slide_count: int
    pattern_order: tuple[str, ...]
    text_density: str
    image_ref_count: int
    expected_review_required: bool


@dataclass(frozen=True)
class PreparedSample:
    prompt_id: str
    case_id: str
    label: str
    prompt: str
    starter_yaml: str
    image_ref_count: int
    expected_review_required: bool
    manifest: dict[str, Any]


def load_case_catalog(path: Path = CASE_CATALOG_PATH) -> dict[str, ManualPublicCase]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, dict) or not raw_cases:
        raise RuntimeError(f"Case catalog is empty: {path}")

    catalog: dict[str, ManualPublicCase] = {}
    for case_id, raw_case in raw_cases.items():
        if not isinstance(raw_case, dict):
            raise RuntimeError(f"Case '{case_id}' must be an object.")
        pattern_order = tuple(str(pattern_id) for pattern_id in raw_case.get("pattern_order", []))
        case = ManualPublicCase(
            case_id=str(case_id),
            label=str(raw_case["label"]),
            body_slide_count=int(raw_case["body_slide_count"]),
            pattern_order=pattern_order,
            text_density=str(raw_case["text_density"]),
            image_ref_count=int(raw_case["image_ref_count"]),
            expected_review_required=bool(raw_case["expected_review_required"]),
        )
        _validate_case(case)
        catalog[case.case_id] = case
    return catalog


def load_suite_map(path: Path = CASE_CATALOG_PATH) -> dict[str, tuple[str, ...]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_suites = payload.get("suites")
    if not isinstance(raw_suites, dict) or not raw_suites:
        raise RuntimeError(f"Suite map is empty: {path}")
    suite_map: dict[str, tuple[str, ...]] = {}
    for suite_name, raw_case_ids in raw_suites.items():
        if not isinstance(raw_case_ids, list) or not raw_case_ids:
            raise RuntimeError(f"Suite '{suite_name}' must define at least 1 case.")
        suite_map[str(suite_name)] = tuple(str(case_id) for case_id in raw_case_ids)
    return suite_map


def expand_suite(
    suite_name: str,
    *,
    path: Path = CASE_CATALOG_PATH,
) -> tuple[ManualPublicCase, ...]:
    catalog = load_case_catalog(path)
    suite_map = load_suite_map(path)
    try:
        case_ids = suite_map[suite_name]
    except KeyError as exc:
        allowed = ", ".join(sorted(suite_map))
        raise RuntimeError(f"Unknown suite '{suite_name}'. Expected one of: {allowed}.") from exc
    cases: list[ManualPublicCase] = []
    for case_id in case_ids:
        try:
            cases.append(catalog[case_id])
        except KeyError as exc:
            raise RuntimeError(f"Suite '{suite_name}' references unknown case '{case_id}'.") from exc
    return tuple(cases)


def prepare_suite_samples(
    suite_name: str,
    *,
    sample_count: int | None = None,
    path: Path = CASE_CATALOG_PATH,
) -> tuple[PreparedSample, ...]:
    cases = expand_suite(suite_name, path=path)
    if sample_count is None:
        selected_cases = cases
    else:
        if sample_count <= 0:
            raise RuntimeError("sample_count must be greater than 0.")
        selected_cases = tuple(cases[index % len(cases)] for index in range(sample_count))
    return tuple(build_prepared_sample(case) for case in selected_cases)


def load_prompt_pack_samples(
    prompt_pack_path: Path,
    *,
    sample_count: int | None = None,
) -> tuple[PreparedSample, ...]:
    raw_payload = json.loads(prompt_pack_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list) or not raw_payload:
        raise RuntimeError(f"Prompt pack is empty: {prompt_pack_path}")

    raw_samples: list[PreparedSample] = []
    for index, item in enumerate(raw_payload, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Prompt pack row {index} must be an object.")
        prompt = str(item["prompt"])
        starter_yaml = str(item.get("starter_yaml") or _extract_starter_yaml(prompt))
        manifest = item.get("case_manifest")
        if not isinstance(manifest, dict):
            manifest = {
                "case_id": str(item.get("case_id") or item.get("prompt_id") or f"prompt-{index:03d}"),
                "label": str(item.get("label") or item.get("prompt_id") or f"Prompt {index}"),
                "body_slide_count": int(item.get("body_slide_count") or 0),
                "pattern_order": list(item.get("pattern_order") or []),
                "text_density": str(item.get("text_density") or "unknown"),
                "image_ref_count": int(item.get("image_ref_count") or 0),
                "expected_review_required": bool(item.get("expected_review_required")),
            }
        raw_samples.append(
            PreparedSample(
                prompt_id=str(item.get("prompt_id") or manifest["case_id"]),
                case_id=str(item.get("case_id") or manifest["case_id"]),
                label=str(item.get("label") or manifest["label"]),
                prompt=prompt,
                starter_yaml=starter_yaml,
                image_ref_count=int(item.get("image_ref_count") or manifest.get("image_ref_count") or 0),
                expected_review_required=bool(
                    item.get("expected_review_required")
                    if "expected_review_required" in item
                    else manifest.get("expected_review_required")
                ),
                manifest=dict(manifest),
            )
        )

    if sample_count is None:
        return tuple(raw_samples)
    if sample_count <= 0:
        raise RuntimeError("sample_count must be greater than 0.")
    return tuple(raw_samples[index % len(raw_samples)] for index in range(sample_count))


def build_prepared_sample(case: ManualPublicCase) -> PreparedSample:
    starter_yaml = render_starter_yaml(case)
    manifest = build_case_manifest(case)
    return PreparedSample(
        prompt_id=case.case_id,
        case_id=case.case_id,
        label=case.label,
        prompt=render_prompt_text(case, starter_yaml=starter_yaml),
        starter_yaml=starter_yaml,
        image_ref_count=case.image_ref_count,
        expected_review_required=case.expected_review_required,
        manifest=manifest,
    )


def build_prompt_pack_payload(
    *,
    suite_name: str = DEFAULT_SUITE_NAME,
    path: Path = CASE_CATALOG_PATH,
) -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": sample.prompt_id,
            "case_id": sample.case_id,
            "label": sample.label,
            "strength": "product",
            "prompt": sample.prompt,
            "starter_yaml": sample.starter_yaml,
            "image_ref_count": sample.image_ref_count,
            "expected_review_required": sample.expected_review_required,
            "case_manifest": sample.manifest,
        }
        for sample in prepare_suite_samples(suite_name, path=path)
    ]


def build_case_manifest(case: ManualPublicCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "label": case.label,
        "body_slide_count": case.body_slide_count,
        "pattern_order": list(case.pattern_order),
        "text_density": case.text_density,
        "image_ref_count": case.image_ref_count,
        "expected_review_required": case.expected_review_required,
    }


def extract_case_manifest_from_payload(raw_data: object) -> dict[str, Any]:
    root = raw_data
    if isinstance(raw_data, dict) and isinstance(raw_data.get("report_content"), dict):
        root = raw_data["report_content"]

    if not isinstance(root, dict):
        return {
            "body_slide_count": 0,
            "pattern_order": [],
            "image_ref_count": 0,
            "image_refs": [],
        }

    raw_slides = root.get("slides")
    if not isinstance(raw_slides, list):
        raw_slides = []

    pattern_order: list[str] = []
    image_refs: list[str] = []
    seen_image_refs: set[str] = set()
    for raw_slide in raw_slides:
        if not isinstance(raw_slide, dict):
            pattern_order.append("")
            continue
        pattern_order.append(str(raw_slide.get("pattern_id", "") or ""))
        slots = raw_slide.get("slots")
        if not isinstance(slots, dict):
            continue
        for key, value in slots.items():
            if not str(key).startswith("image_"):
                continue
            ref = str(value or "").strip()
            if not ref or ref in seen_image_refs:
                continue
            seen_image_refs.add(ref)
            image_refs.append(ref)

    return {
        "body_slide_count": len(raw_slides),
        "pattern_order": pattern_order,
        "image_ref_count": len(image_refs),
        "image_refs": image_refs,
    }


def extract_case_manifest_from_yaml(yaml_candidate: str) -> dict[str, Any]:
    return extract_case_manifest_from_payload(parse_yaml_text(yaml_candidate))


def validate_yaml_candidate_against_manifest(
    yaml_candidate: str,
    *,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_body_slide_count = int(manifest.get("body_slide_count", 0) or 0)
    expected_pattern_order = [str(item) for item in list(manifest.get("pattern_order", []) or [])]
    expected_image_ref_count = int(manifest.get("image_ref_count", 0) or 0)
    expected_image_refs = [f"image_{index}" for index in range(1, expected_image_ref_count + 1)]

    try:
        actual = extract_case_manifest_from_yaml(yaml_candidate)
    except yaml.YAMLError as exc:
        errors.append(f"Case manifest guard could not parse the YAML candidate: {exc}")
        actual = {
            "body_slide_count": 0,
            "pattern_order": [],
            "image_ref_count": 0,
            "image_refs": [],
        }

    actual_body_slide_count = int(actual.get("body_slide_count", 0) or 0)
    actual_pattern_order = [str(item) for item in list(actual.get("pattern_order", []) or [])]
    actual_image_ref_count = int(actual.get("image_ref_count", 0) or 0)
    actual_image_refs = [str(item) for item in list(actual.get("image_refs", []) or [])]

    if actual_body_slide_count != expected_body_slide_count:
        errors.append(
            "Case manifest guard expected "
            f"{expected_body_slide_count} body slide(s), but the YAML candidate defines "
            f"{actual_body_slide_count}."
        )
    if actual_pattern_order != expected_pattern_order:
        errors.append(
            "Case manifest guard expected pattern_order "
            f"{expected_pattern_order}, but the YAML candidate produced {actual_pattern_order}."
        )
    if actual_image_ref_count != expected_image_ref_count:
        errors.append(
            "Case manifest guard expected "
            f"{expected_image_ref_count} upload ref(s), but the YAML candidate produced "
            f"{actual_image_ref_count}: {actual_image_refs}."
        )
    elif actual_image_refs != expected_image_refs:
        errors.append(
            "Case manifest guard expected the exact upload refs "
            f"{expected_image_refs}, but the YAML candidate used {actual_image_refs}."
        )

    return {
        "ok": not errors,
        "message": (
            "Case manifest guard passed."
            if not errors
            else f"Case manifest guard found {len(errors)} blocking issue(s)."
        ),
        "errors": errors,
        "expected": {
            "body_slide_count": expected_body_slide_count,
            "pattern_order": expected_pattern_order,
            "image_ref_count": expected_image_ref_count,
            "image_refs": expected_image_refs,
        },
        "actual": {
            "body_slide_count": actual_body_slide_count,
            "pattern_order": actual_pattern_order,
            "image_ref_count": actual_image_ref_count,
            "image_refs": actual_image_refs,
        },
    }


def render_prompt_text(
    case: ManualPublicCase,
    *,
    starter_yaml: str | None = None,
) -> str:
    rendered_starter = starter_yaml or render_starter_yaml(case)
    return (
        f"{MANUAL_DRAFT_PROMPT_HEADER}\n"
        f"{rendered_starter}\n"
        f"{MANUAL_DRAFT_PROMPT_FOOTER}"
    ).strip()


def render_starter_yaml(case: ManualPublicCase) -> str:
    document = {"report_content": build_report_content(case)}
    return _serialize_prompt_yaml(document).strip()


def build_report_content(case: ManualPublicCase) -> dict[str, object]:
    slides: list[dict[str, object]] = []
    current_section_index = 1
    current_step_index = 0
    next_image_index = 1

    for slide_index, pattern_id in enumerate(case.pattern_order, start=1):
        if pattern_id == "text.manual.section_break":
            if slides:
                current_section_index += 1
            current_step_index = 0
            slides.append(
                {
                    "pattern_id": pattern_id,
                    "slots": {
                        "section_no": f"{current_section_index}.",
                        "section_title": f"{case.label} Section {current_section_index}",
                        "section_subtitle": (
                            f"Manual regression setup for {case.case_id} with {case.text_density} text density."
                        ),
                    },
                }
            )
            continue

        current_step_index += 1
        image_count = _PATTERN_IMAGE_COUNTS[pattern_id]
        title = _procedure_title(pattern_id=pattern_id, slide_index=slide_index)
        summary = _procedure_summary(case=case, pattern_id=pattern_id, step_index=current_step_index)
        detail_body = _procedure_detail_body(case=case, pattern_id=pattern_id, step_index=current_step_index)
        slots: dict[str, object] = {
            "step_no": f"{current_section_index}.{current_step_index}",
            "step_title": title,
            "command_or_action": (
                f"Action: validate the {title.lower()} state and capture the matching evidence screenshot."
            ),
            "summary": summary,
            "detail_body": detail_body,
        }
        for image_offset in range(image_count):
            ref = f"image_{next_image_index + image_offset}"
            slots[f"image_{image_offset + 1}"] = ref
            slots[f"caption_{image_offset + 1}"] = (
                f"{case.case_id} screenshot {image_offset + 1} for {title}"
            )
        next_image_index += image_count
        slides.append(
            {
                "pattern_id": pattern_id,
                "slots": slots,
            }
        )

    return {
        "title_slide": {
            "pattern_id": "cover.manual",
            "slots": {
                "doc_title": f"Autoreport Manual Regression {case.case_id}",
                "doc_subtitle": (
                    f"{case.label} generated starter for the public manual AI verification flow."
                ),
                "doc_version": "v0.4.2",
                "author_or_owner": "Autoreport Verification",
            },
        },
        "contents_slide": {
            "pattern_id": "contents.manual",
            "slots": {
                "contents_title": "Contents",
                "contents_group_label": f"{case.label} Walkthrough",
            },
        },
        "slides": slides,
    }


def _procedure_title(*, pattern_id: str, slide_index: int) -> str:
    if pattern_id == "text_image.manual.procedure.two":
        return f"Compare Two Screens {slide_index}"
    if pattern_id == "text_image.manual.procedure.three":
        return f"Track Three Stage Flow {slide_index}"
    return _ONE_IMAGE_LABELS.get(pattern_id, f"Procedure Step {slide_index}")


def _procedure_summary(
    *,
    case: ManualPublicCase,
    pattern_id: str,
    step_index: int,
) -> str:
    layout_label = _ONE_IMAGE_LABELS.get(pattern_id, pattern_id)
    if case.text_density == "concise":
        return (
            f"Confirm step {step_index} in the {layout_label.lower()} layout with the required screenshots."
        )
    if case.text_density == "dense":
        return (
            f"Document the operator action, visible confirmation, and regression purpose for step {step_index} in the {layout_label.lower()} layout."
        )
    return (
        f"Explain step {step_index} in the {layout_label.lower()} layout and show the visible before and after cues needed for regression."
    )


def _procedure_detail_body(
    *,
    case: ManualPublicCase,
    pattern_id: str,
    step_index: int,
) -> str:
    pattern_label = _ONE_IMAGE_LABELS.get(pattern_id, pattern_id).lower()
    paragraphs = _TEXT_DENSITY_PARAGRAPHS[case.text_density]
    lines = [f"Case {case.case_id} uses the {pattern_label} pattern for this step."]
    lines.extend(paragraphs)
    lines.append(
        f"Finish step {step_index} only after the completion cue is clearly visible in the slide."
    )
    return "\n".join(lines)


def _extract_starter_yaml(prompt: str) -> str:
    marker = "report_content:"
    marker_index = prompt.find(marker)
    if marker_index < 0:
        return ""
    starter = prompt[marker_index:]
    footer_marker = f"\n{MANUAL_DRAFT_PROMPT_FOOTER.splitlines()[0]}"
    footer_index = starter.find(footer_marker)
    if footer_index >= 0:
        starter = starter[:footer_index]
    return starter.strip()


class _PromptYamlDumper(yaml.SafeDumper):
    pass


def _represent_prompt_scalar(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_PromptYamlDumper.add_representer(str, _represent_prompt_scalar)


def _serialize_prompt_yaml(document: dict[str, object]) -> str:
    return yaml.dump(
        document,
        Dumper=_PromptYamlDumper,
        sort_keys=False,
        allow_unicode=True,
    )


def _validate_case(case: ManualPublicCase) -> None:
    if case.body_slide_count != len(case.pattern_order):
        raise RuntimeError(
            f"Case '{case.case_id}' body_slide_count does not match pattern_order length."
        )
    if case.text_density not in _TEXT_DENSITY_PARAGRAPHS:
        allowed = ", ".join(sorted(_TEXT_DENSITY_PARAGRAPHS))
        raise RuntimeError(
            f"Case '{case.case_id}' uses unsupported text_density '{case.text_density}'. Expected one of: {allowed}."
        )
    unknown_patterns = [
        pattern_id for pattern_id in case.pattern_order if pattern_id not in MANUAL_ALLOWED_BODY_PATTERN_IDS
    ]
    if unknown_patterns:
        raise RuntimeError(
            f"Case '{case.case_id}' references unsupported patterns: {', '.join(unknown_patterns)}."
        )
    computed_image_count = sum(_PATTERN_IMAGE_COUNTS[pattern_id] for pattern_id in case.pattern_order)
    if computed_image_count != case.image_ref_count:
        raise RuntimeError(
            f"Case '{case.case_id}' image_ref_count={case.image_ref_count} but computed {computed_image_count}."
        )
    if case.expected_review_required and case.case_id not in REVIEW_CASE_IDS:
        raise RuntimeError(
            f"Case '{case.case_id}' is marked for review but is not a fixed representative review case."
        )
