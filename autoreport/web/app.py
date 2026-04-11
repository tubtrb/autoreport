"""FastAPI application for the public Autoreport demo."""

from __future__ import annotations

import base64
from difflib import get_close_matches
from html import escape
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.background import BackgroundTask

from autoreport.engine.generator import generate_report_from_mapping
from autoreport.loader import parse_yaml_text
from autoreport.template_flow import (
    PUBLIC_BUILT_IN_TEMPLATE_NAME,
    detect_payload_kind,
    get_built_in_contract,
    get_built_in_profile,
    materialize_authoring_payload,
    materialize_report_payload,
    serialize_document,
)
from autoreport.templates.weekly_report import build_report_fill_plan
from autoreport.validator import ValidationError
from autoreport.web.style_presets import (
    MANUAL_PUBLIC_TEMPLATE_NAME as STYLE_PRESET_MANUAL_TEMPLATE_NAME,
    append_style_preset_to_payload_yaml,
    delete_manual_slide_from_payload_yaml,
    default_style_preset_id,
    get_style_preset_catalog,
)


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg"}
MANUAL_PUBLIC_TEMPLATE_NAME = STYLE_PRESET_MANUAL_TEMPLATE_NAME
PUBLIC_WEB_TEMPLATE_NAMES = (
    PUBLIC_BUILT_IN_TEMPLATE_NAME,
    MANUAL_PUBLIC_TEMPLATE_NAME,
)
DEFAULT_SLIDE_WIDTH_EMU = 9144000
DEFAULT_SLIDE_HEIGHT_EMU = 6858000
PREVIEW_PLACEHOLDER_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)
PUBLIC_WEB_IMAGE_DISABLED_ERRORS = [
    "The public web demo currently supports text and metrics slides only.",
    "Remove text_image patterns and image_* slots, or use the debug app or CLI for image-backed decks.",
]

_EDITORIAL_CONTRACT = get_built_in_contract(PUBLIC_BUILT_IN_TEMPLATE_NAME)
_MANUAL_CONTRACT = get_built_in_contract(MANUAL_PUBLIC_TEMPLATE_NAME)
_MANUAL_ALLOWED_BODY_PATTERNS = (
    (
        "text.manual.section_break",
        0,
        "Use for text-only divider slides with no image_* slots.",
    ),
    (
        "text_image.manual.procedure.one",
        1,
        "Use when the slide has exactly 1 image_* slot.",
    ),
    (
        "text_image.manual.procedure.two",
        2,
        "Use when the slide has exactly 2 image_* slots.",
    ),
    (
        "text_image.manual.procedure.three",
        3,
        "Use when the slide has exactly 3 image_* slots.",
    ),
)
_MANUAL_ALLOWED_BODY_PATTERN_IDS = tuple(
    pattern_id for pattern_id, _, _ in _MANUAL_ALLOWED_BODY_PATTERNS
)
_MANUAL_ALLOWED_PATTERN_BY_IMAGE_COUNT = {
    image_count: pattern_id
    for pattern_id, image_count, _ in _MANUAL_ALLOWED_BODY_PATTERNS
}
_MANUAL_DASH_STEP_NO_RE = re.compile(r"^\d+-\d+$")
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
_MANUAL_AI_AUTO_REPAIR_WARNING = (
    "Auto-corrected common manual YAML indentation drift before checking."
)
_MANUAL_AI_AUTO_REPAIR_HINT = (
    "The draft was re-indented automatically. Review the repaired YAML in the editor before generating."
)
MANUAL_DRAFT_PROMPT_YAML = """
# Paste this brief into another AI and ask it to fill the report_content draft below.
# Goal: draft a screenshot-first procedure manual for Autoreport using the manual template.
# Hard rules:
# - Return exactly one YAML document rooted at report_content.
# - Do not write prose before or after the YAML.
# - Keep title_slide.pattern_id exactly as cover.manual.
# - Keep contents_slide.pattern_id exactly as contents.manual when a contents slide is present.
# - Only use these body pattern_id values:
#   - text.manual.section_break
#   - text_image.manual.procedure.one
#   - text_image.manual.procedure.two
#   - text_image.manual.procedure.three
# - Never invent new pattern_id names such as image.manual.step.
# - Use text.manual.section_break only for text-only divider slides with no image_* slots.
# - Use text_image.manual.procedure.one only when exactly 1 image_* slot is present.
# - Use text_image.manual.procedure.two only when exactly 2 image_* slots are present.
# - Use text_image.manual.procedure.three only when exactly 3 image_* slots are present.
# - Keep image slot values as upload refs in the listed order (for example image_1, image_2, image_3).
# - Use step numbers like 2.1, 2.2, 3.1. Do not write 2-1 or 3-1.
# - Fill short manual fields such as step_no, step_title, command_or_action, and summary directly.
# - Put long procedure text into detail_body.
# - Add caption_1..caption_3 only when the image needs a short caption.
report_content:
  title_slide:
    pattern_id: cover.manual
    slots:
      doc_title: Replace with the guide title
      doc_subtitle: |
        Replace with a concise guide subtitle
      doc_version: v0.4.2
      author_or_owner: Autoreport Team
  contents_slide:
    pattern_id: contents.manual
    slots:
      contents_title: Contents
      contents_group_label: Procedure Overview
  slides:
    - pattern_id: text.manual.section_break
      slots:
        section_no: "1."
        section_title: First section title
        section_subtitle: Short section setup note
    - pattern_id: text_image.manual.procedure.one
      slots:
        step_no: "1.1"
        step_title: First procedure title
        command_or_action: "Command or action for this step"
        summary: Short outcome summary for the step
        detail_body: |
          Explain the detailed procedure here.
        image_1: image_1
        caption_1: First screenshot caption
""".strip()
MANUAL_PROCEDURE_EXAMPLE_YAML = f"""
report_content:
  title_slide:
    pattern_id: cover.manual
    slots:
      doc_title: Autoreport PowerPoint User Guide
      doc_subtitle: |
        Screenshot-first guide for the public web manual mode
      doc_version: v0.4.2
      author_or_owner: Autoreport Team
  contents_slide:
    pattern_id: contents.manual
    slots:
      contents_title: Contents
      contents_group_label: Procedure Overview
  slides:
    - pattern_id: text.manual.section_break
      slots:
        section_no: "1."
        section_title: Review The Manual Starter
        section_subtitle: Start with the built-in manual procedure starter before editing content.
    - pattern_id: text_image.manual.procedure.one
      slots:
        step_no: "1.1"
        step_title: Review The Starter Example
        command_or_action: "Action: open the starter example and confirm the selected template."
        summary: Use one screenshot to show the starting editor state.
        detail_body: |
          Review the starter YAML, note the built-in template mode, and confirm
          the page is ready before moving to the next step.
        image_1: image_1
        caption_1: Starter example loaded in the editor
    - pattern_id: text_image.manual.procedure.two
      slots:
        step_no: "1.2"
        step_title: Customize The Draft
        command_or_action: "Action: edit the YAML title, sections, and example copy."
        summary: Use the ordered screenshots to compare the starter draft before and after the edits.
        detail_body: |
          Update the guide title and slide text, then compare the edited YAML
          against the original starter so the customer can see what changed.
        image_1: image_2
        image_2: image_3
        caption_1: Starter YAML before editing
        caption_2: Starter YAML after editing
    - pattern_id: text_image.manual.procedure.three
      slots:
        step_no: "1.3"
        step_title: Generate The PowerPoint
        command_or_action: "Action: refresh the slide order and generate the PowerPoint deck."
        summary: Use three screenshots to document preview, generation, and download.
        detail_body: |
          Refresh the manual slide order, confirm the PowerPoint preview, and
          generate the deck so the download step is visible end to end.
        image_1: image_4
        image_2: image_5
        image_3: image_6
        caption_1: Slide preview ready
        caption_2: Generation in progress
        caption_3: PowerPoint download complete
""".strip()
MANUAL_DRAFT_PROMPT_HEADER = MANUAL_DRAFT_PROMPT_YAML.partition("\nreport_content:")[0].strip()
PROMPTED_MANUAL_PROCEDURE_EXAMPLE_YAML = (
    f"{MANUAL_DRAFT_PROMPT_HEADER}\n{MANUAL_PROCEDURE_EXAMPLE_YAML}"
).strip()
app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_style_family_filters(families: list[dict[str, object]]) -> str:
    buttons = [
        (
            '                <button type="button" class="style-family-chip is-selected" '
            'data-family-filter="all" aria-pressed="true">All</button>'
        )
    ]
    for family in families:
        family_id = escape(str(family["family_id"]), quote=True)
        label = escape(str(family["label"]))
        buttons.append(
            '                <button type="button" class="style-family-chip" '
            f'data-family-filter="{family_id}" aria-pressed="false">{label}</button>'
        )
    return "\n".join(buttons)


def _render_style_thumbnail_svg(thumbnail: dict[str, object]) -> str:
    background = escape(str(thumbnail.get("background", "#f8fafc")), quote=True)
    block_nodes: list[str] = [
        (
            '                  <rect x="0" y="0" width="100" height="100" '
            f'rx="18" fill="{background}"></rect>'
        )
    ]
    for block in thumbnail.get("blocks", []):
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type", "rect"))
        role = str(block.get("role", "text"))
        fill_color = {
            "accent": "#0b6a58",
            "image": "#cfe7e0",
            "circle": "#dcecf6",
            "text": "#9fb4c8",
        }.get(role, "#cbd5e1")
        stroke = ' stroke="rgba(91,104,122,0.28)" stroke-width="0.8"' if role == "image" else ""
        if block_type == "circle":
            block_nodes.append(
                "                  "
                f'<circle cx="{block.get("cx", 50)}" cy="{block.get("cy", 50)}" '
                f'r="{block.get("r", 12)}" fill="{fill_color}"{stroke}></circle>'
            )
            continue
        block_nodes.append(
            "                  "
            f'<rect x="{block.get("x", 0)}" y="{block.get("y", 0)}" '
            f'width="{block.get("w", 10)}" height="{block.get("h", 10)}" '
            f'rx="{block.get("radius", 6)}" fill="{fill_color}"{stroke}></rect>'
        )
    return "\n".join(
        [
            '                <svg viewBox="0 0 100 100" class="style-preset-thumb-svg" aria-hidden="true">',
            *block_nodes,
            "                </svg>",
        ]
    )


def _render_style_preset_cards(
    presets: list[dict[str, object]],
    *,
    selected_preset_id: str | None,
) -> str:
    cards: list[str] = []
    for preset in presets:
        preset_id = str(preset["preset_id"])
        selected = preset_id == selected_preset_id
        family_id = escape(str(preset["family_id"]), quote=True)
        pattern_id = escape(str(preset["pattern_id"]), quote=True)
        label = escape(str(preset["label"]))
        description = escape(str(preset["description"]))
        tag_markup = "".join(
            f'<span class="style-preset-tag">{escape(str(tag))}</span>'
            for tag in preset.get("tags", [])
        )
        cards.append(
            "\n".join(
                [
                    "              "
                    f'<button type="button" class="style-preset-card{" is-selected" if selected else ""}" '
                    f'data-preset-id="{escape(preset_id, quote=True)}" '
                    f'data-family-id="{family_id}" '
                    f'data-pattern-id="{pattern_id}" '
                    f'aria-pressed="{"true" if selected else "false"}">',
                    '                <div class="style-preset-thumb">',
                    _render_style_thumbnail_svg(preset["thumbnail"]),
                    "                </div>",
                    '                <div class="style-preset-meta">',
                    f'                  <div class="style-preset-name">{label}</div>',
                    f'                  <div class="style-preset-description">{description}</div>',
                    f'                  <div class="style-preset-tags">{tag_markup}</div>',
                    "                </div>",
                    "              </button>",
                ]
            )
        )
    return "\n".join(cards)


def _render_demo_html() -> str:
    style_catalog = get_style_preset_catalog(MANUAL_PUBLIC_TEMPLATE_NAME)
    prompted_manual_example_json = json.dumps(PROMPTED_MANUAL_PROCEDURE_EXAMPLE_YAML)
    manual_template_name_json = json.dumps(MANUAL_PUBLIC_TEMPLATE_NAME)
    style_catalog_json = json.dumps(style_catalog)
    default_preset_id = default_style_preset_id(MANUAL_PUBLIC_TEMPLATE_NAME)
    family_filters_html = _render_style_family_filters(style_catalog["families"])
    preset_cards_html = _render_style_preset_cards(
        style_catalog["presets"],
        selected_preset_id=default_preset_id,
    )
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autoreport Demo</title>
    <style>
      :root {
        --bg: #f4f1e8;
        --surface: #ffffff;
        --panel: #f8fafc;
        --text: #172033;
        --muted: #5b687a;
        --accent: #0b6a58;
        --accent-soft: #e8f8f2;
        --border: #d5deea;
        --shadow: 0 24px 52px rgba(15, 23, 42, 0.08);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top right, rgba(11,106,88,0.08), transparent 24%),
          linear-gradient(180deg, rgba(11,106,88,0.05), transparent 32%),
          var(--bg);
        color: var(--text);
        font-family: "Segoe UI", Arial, sans-serif;
      }
      main { max-width: 1560px; margin: 0 auto; padding: 36px 24px 56px; }
      h1 { margin: 0 0 12px; text-align: center; color: var(--accent); font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -0.04em; }
      .hero-copy { max-width: 880px; margin: 0 auto 28px; text-align: center; color: var(--muted); line-height: 1.7; }
      .card { background: var(--surface); border: 1px solid rgba(15,23,42,0.06); border-radius: 24px; box-shadow: var(--shadow); padding: 28px; }
      .workspace { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; align-items: start; }
      .workspace.manual-layout { grid-template-columns: minmax(700px, 1.45fr) minmax(560px, 1.02fr); }
      .panel, .rail-box { min-width: 0; }
      .rail { display: grid; gap: 16px; align-self: start; position: sticky; top: 20px; }
      .panel h2, .rail-box h2 { margin: 0 0 8px; font-size: 1rem; }
      .panel-copy, .footnote { color: var(--muted); line-height: 1.6; font-size: 0.95rem; }
      .panel-head {
        display: grid;
        gap: 10px;
      }
      .panel-head-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
      }
      .starter-pill {
        padding: 8px 14px;
        border: 1px solid rgba(11,106,88,0.16);
        border-radius: 999px;
        background: rgba(232,248,242,0.8);
        color: var(--accent);
        font-size: 0.84rem;
        font-weight: 800;
        white-space: nowrap;
      }
      .panel { display: grid; gap: 16px; }
      textarea {
        width: 100%;
        min-height: clamp(320px, 40vh, 520px);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        background: var(--panel);
        color: var(--text);
        font: 0.9rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      textarea[readonly] { opacity: 0.94; }
      button {
        border: none;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      button:disabled {
        cursor: wait;
        opacity: 0.72;
      }
      .ghost { background: var(--accent-soft); color: var(--accent); }
      .secondary {
        background: rgba(11,106,88,0.12);
        color: var(--accent);
        border: 1px solid rgba(11,106,88,0.18);
      }
      .primary { width: 100%; padding: 14px 18px; border-radius: 16px; background: var(--accent); color: #fff; }
      .rail-box { border: 1px solid var(--border); border-radius: 18px; background: var(--panel); padding: 18px; }
      .status-errors, .status-hints { margin: 12px 0 0; padding-left: 18px; line-height: 1.6; }
      .status-errors { color: #b91c1c; }
      .status-hints { color: var(--accent); }
      .slide-upload-slot input[type=file] {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 8px 10px;
        background: #fff;
        color: var(--text);
        font: inherit;
      }
      .slide-preview-box[hidden], .style-gallery[hidden] { display: none; }
      .style-gallery {
        display: grid;
        gap: 14px;
        padding: 18px;
        border: 1px solid var(--border);
        border-radius: 20px;
        background: linear-gradient(180deg, rgba(248,250,252,0.98), rgba(255,255,255,1));
      }
      .style-gallery-head {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 12px;
      }
      .style-family-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .style-family-chip {
        padding: 8px 14px;
        border: 1px solid var(--border);
        border-radius: 999px;
        background: #fff;
        color: var(--text);
        font-size: 0.86rem;
      }
      .style-family-chip.is-selected {
        border-color: rgba(11,106,88,0.24);
        background: var(--accent-soft);
        color: var(--accent);
      }
      .style-preset-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .style-preset-card {
        display: grid;
        grid-template-columns: 132px minmax(0, 1fr);
        gap: 12px;
        align-items: center;
        padding: 12px;
        border: 1px solid var(--border);
        border-radius: 18px;
        background: #fff;
        text-align: left;
      }
      .style-preset-card[hidden] { display: none; }
      .style-preset-card:hover {
        border-color: rgba(11,106,88,0.22);
        box-shadow: 0 18px 32px rgba(15, 23, 42, 0.06);
      }
      .style-preset-card.is-selected {
        border-color: rgba(11,106,88,0.3);
        background: linear-gradient(180deg, rgba(232,248,242,0.84), #ffffff);
        box-shadow: 0 18px 36px rgba(11,106,88,0.08);
      }
      .style-preset-thumb {
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 16px;
        background: #f8fafc;
        overflow: hidden;
      }
      .style-preset-thumb-svg {
        display: block;
        width: 100%;
        height: auto;
      }
      .style-preset-meta {
        display: grid;
        gap: 8px;
        min-width: 0;
      }
      .style-preset-name {
        font-size: 0.97rem;
        font-weight: 800;
        color: var(--text);
      }
      .style-preset-description {
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.5;
      }
      .style-preset-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .style-preset-tag {
        padding: 4px 8px;
        border-radius: 999px;
        background: rgba(15,23,42,0.05);
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 700;
      }
      .action-bar {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
      }
      .slide-preview-box {
        border: 1px solid var(--border);
        border-radius: 18px;
        background: rgba(255,255,255,0.96);
        padding: 18px;
      }
      .slide-preview-list {
        list-style: none;
        padding: 0;
        margin: 12px 0 0;
        display: grid;
        gap: 14px;
      }
      .preview-status {
        display: grid;
        gap: 10px;
        margin-bottom: 14px;
      }
      .preview-status-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .draft-check-box {
        display: grid;
        gap: 10px;
        padding: 14px;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(248,250,252,0.92), #ffffff);
        margin-bottom: 14px;
      }
      .link-button {
        padding: 0;
        border-radius: 0;
        background: transparent;
        color: var(--accent);
        font-size: 0.84rem;
        font-weight: 700;
      }
      .draft-check-warnings {
        margin: 0;
        padding-left: 18px;
        line-height: 1.6;
        color: #a16207;
      }
      .slide-preview-row {
        display: grid;
        gap: 12px;
      }
      .slide-preview-row.has-upload {
        grid-template-columns: minmax(220px, 0.54fr) minmax(0, 1fr);
        align-items: start;
      }
      .slide-upload-card,
      .slide-card {
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 10px;
        background: #fff;
      }
      .slide-upload-card {
        background: linear-gradient(180deg, rgba(11,106,88,0.04), #ffffff);
      }
      .slide-card-head {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .slide-card-title {
        font-weight: 700;
        font-size: 0.95rem;
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
      }
      .slide-card-meta {
        color: var(--muted);
        font-size: 0.75rem;
        white-space: nowrap;
      }
      .slide-card-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
        min-width: 0;
      }
      .slide-delete-button {
        padding: 6px 12px;
        border: 1px solid rgba(185,28,28,0.16);
        border-radius: 999px;
        background: rgba(185,28,28,0.08);
        color: #b91c1c;
        font-size: 0.76rem;
        line-height: 1.2;
        font-weight: 800;
      }
      .slide-delete-button:disabled {
        cursor: wait;
      }
      .slide-upload-panel {
        display: grid;
        gap: 8px;
      }
      .slide-upload-slot {
        display: grid;
        gap: 6px;
        padding: 8px;
        border: 1px dashed rgba(91,104,122,0.35);
        border-radius: 14px;
        background: #fff;
        outline: none;
      }
      .slide-upload-slot.is-active,
      .slide-upload-slot:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(11,106,88,0.12);
      }
      .slide-upload-slot-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      .slide-upload-slot-title {
        font-weight: 700;
        color: var(--text);
      }
      .slide-upload-slot-state {
        color: var(--muted);
        font-size: 0.78rem;
      }
      .slide-upload-slot-copy {
        display: none;
      }
      .slide-upload-actions {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 8px;
        align-items: center;
      }
      .slide-upload-actions input[type=file] {
        min-width: 0;
        font-size: 0.82rem;
      }
      .slide-upload-clear {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 7px 10px;
        background: #fff;
        color: var(--text);
        font-size: 0.82rem;
        line-height: 1.2;
        font-weight: 700;
        cursor: pointer;
        white-space: nowrap;
      }
      .slide-upload-file-name {
        color: var(--accent);
        font-size: 0.78rem;
        word-break: break-word;
      }
      .slide-canvas {
        position: relative;
        aspect-ratio: 4 / 3;
        overflow: hidden;
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 16px;
        background: linear-gradient(180deg, #ffffff, #f7fafc);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
      }
      .slide-canvas.manual {
        background:
          linear-gradient(135deg, rgba(22,78,99,0.08), transparent 34%),
          linear-gradient(180deg, #f8fafc, #eef4f7);
      }
      .slide-canvas.editorial {
        background:
          radial-gradient(circle at top right, rgba(11,106,88,0.08), transparent 20%),
          linear-gradient(180deg, #ffffff, #f6fbf9);
      }
      .slide-svg {
        display: block;
        width: 100%;
        height: 100%;
      }
      .status-copy {
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }
      code { font-family: "Cascadia Mono", Consolas, monospace; }
      @media (max-width: 1240px) {
        .workspace.manual-layout { grid-template-columns: 1fr; }
        .rail { position: static; }
      }
      @media (max-width: 1080px) {
        .slide-preview-row.has-upload { grid-template-columns: 1fr; }
        .style-preset-grid { grid-template-columns: 1fr; }
      }
      @media (max-width: 980px) {
        .action-bar { grid-template-columns: 1fr; }
        .style-preset-card { grid-template-columns: 1fr; }
      }
      @media (max-width: 640px) {
        main { padding: 20px 12px 40px; }
        .card { padding: 16px; border-radius: 20px; }
        .hero-copy { margin-bottom: 20px; }
        .rail,
        .panel,
        .preview-status {
          gap: 12px;
        }
        .rail-box,
        .style-gallery,
        .slide-preview-box {
          padding: 14px;
        }
        textarea {
          min-height: 280px;
          padding: 14px;
          font-size: 0.85rem;
        }
        button {
          min-height: 44px;
        }
        .panel-head-top,
        .style-gallery-head,
        .preview-status-head,
        .slide-card-head,
        .slide-upload-slot-head,
        .slide-upload-actions {
          grid-template-columns: 1fr;
          align-items: stretch;
        }
        .panel-head-top,
        .style-gallery-head,
        .preview-status-head,
        .slide-upload-slot-head {
          display: grid;
        }
        .starter-pill {
          width: 100%;
          text-align: center;
          white-space: normal;
        }
        .style-family-chip-row {
          flex-wrap: nowrap;
          overflow-x: auto;
          padding-bottom: 4px;
          scrollbar-width: thin;
        }
        .style-family-chip {
          flex: 0 0 auto;
        }
        .slide-card-title,
        .slide-card-meta {
          white-space: normal;
        }
        .slide-card-actions {
          justify-content: flex-start;
        }
        .slide-upload-clear {
          width: 100%;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Edit the starter deck and generate an Autoreport PPTX.</h1>
      <p class="hero-copy">
        Start from the built-in manual procedure starter below. The public demo
        now focuses on the screenshot-first manual flow with paired upload and
        preview rows for each image-bearing slide.
      </p>
      <section class="card">
        <div id="workspace" class="workspace manual-layout">
          <div class="panel">
            <div class="panel-head">
              <div class="panel-head-top">
                <h2>Starter Deck YAML</h2>
                <span class="starter-pill">Manual Procedure Starter</span>
              </div>
              <p class="panel-copy">
                Start from the built-in manual starter with the AI prompt
                comments at the top. Edit the YAML first, then use the style
                gallery to add or remove manual slides before generating.
              </p>
            </div>
            <textarea id="payload-yaml" aria-label="Working draft"></textarea>
            <div id="style-gallery" class="style-gallery" hidden>
              <div class="style-gallery-head">
                <div>
                  <h2>Slide Style Gallery</h2>
                  <p class="panel-copy">
                    Filter by structure, pick a preset card, and append it to
                    the current manual draft.
                  </p>
                </div>
              </div>
              <div id="style-family-filters" class="style-family-chip-row" aria-label="Slide style families">
__STYLE_FAMILY_FILTERS_HTML__
              </div>
              <div id="style-preset-grid" class="style-preset-grid" aria-label="Slide preset gallery">
__STYLE_PRESET_CARDS_HTML__
              </div>
            </div>
            <div class="action-bar">
              <button id="reset-starter" class="ghost" type="button">Reset Starter Example</button>
              <button id="add-slide-button" class="secondary" type="button">Add Slide</button>
              <button id="check-draft-button" class="secondary" type="button">Check Draft</button>
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
          </div>
          <aside id="manual-rail" class="rail" hidden>
            <div id="slide-preview-box" class="rail-box slide-preview-box" hidden>
              <div class="preview-status">
                <div class="preview-status-head">
                  <h2>Status</h2>
                  <button id="refresh-preview" class="link-button" type="button">Refresh Preview</button>
                </div>
                <div id="status-message" class="panel-copy">
                  The built-in manual procedure starter is loaded with the AI
                  prompt comments. Edit the draft, add or remove slides,
                  and generate the PPTX.
                </div>
                <ul id="status-errors" class="status-errors"></ul>
                <ul id="status-hints" class="status-hints"></ul>
              </div>
              <div id="draft-check-box" class="draft-check-box">
                <div class="preview-status-head">
                  <h2>Draft Checker</h2>
                  <button id="draft-check-link" class="link-button" type="button">Check Draft</button>
                </div>
                <div id="draft-check-message" class="panel-copy">
                  Run Check Draft before generating to catch invalid slide patterns and numbering issues.
                </div>
                <ul id="draft-check-errors" class="status-errors"></ul>
                <ul id="draft-check-warnings" class="draft-check-warnings"></ul>
                <ul id="draft-check-hints" class="status-hints"></ul>
              </div>
              <h2>PowerPoint Slide Preview</h2>
              <p class="panel-copy">
                Slides that need screenshots show a matching upload panel on the
                left so the controls stay aligned with the composed preview on
                the right.
              </p>
              <ul id="slide-preview-list" class="slide-preview-list"></ul>
            </div>
          </aside>
        </div>
      </section>
    </main>
    <script>
      const PROMPTED_MANUAL_PROCEDURE_EXAMPLE = __PROMPTED_MANUAL_EXAMPLE_JSON__;
      const MANUAL_TEMPLATE_NAME = __MANUAL_TEMPLATE_NAME_JSON__;
      const STYLE_PRESET_CATALOG = __STYLE_PRESET_CATALOG_JSON__;
      const DEFAULT_STYLE_PRESET_ID = __DEFAULT_STYLE_PRESET_ID_JSON__;
      const workspace = document.getElementById("workspace");
      const payloadNode = document.getElementById("payload-yaml");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const statusHints = document.getElementById("status-hints");
      const styleGallery = document.getElementById("style-gallery");
      const styleFamilyFilters = document.getElementById("style-family-filters");
      const stylePresetGrid = document.getElementById("style-preset-grid");
      const manualRail = document.getElementById("manual-rail");
      const slidePreviewBox = document.getElementById("slide-preview-box");
      const slidePreviewList = document.getElementById("slide-preview-list");
      const refreshPreviewButton = document.getElementById("refresh-preview");
      const addSlideButton = document.getElementById("add-slide-button");
      const checkDraftButton = document.getElementById("check-draft-button");
      const draftCheckLink = document.getElementById("draft-check-link");
      const draftCheckMessage = document.getElementById("draft-check-message");
      const draftCheckErrors = document.getElementById("draft-check-errors");
      const draftCheckWarnings = document.getElementById("draft-check-warnings");
      const draftCheckHints = document.getElementById("draft-check-hints");

      let requiredImages = [];
      let selectedFilesByRef = new Map();
      let slidePreviews = [];
      let uploadedImageUrls = new Map();
      let activePasteRef = null;
      let activeFamilyFilter = "all";
      const stylePresetById = new Map((STYLE_PRESET_CATALOG.presets || []).map((preset) => [preset.preset_id, preset]));
      let selectedPresetId = DEFAULT_STYLE_PRESET_ID && stylePresetById.has(DEFAULT_STYLE_PRESET_ID)
        ? DEFAULT_STYLE_PRESET_ID
        : (STYLE_PRESET_CATALOG.presets?.[0]?.preset_id || null);
      const SVG_NS = "http://www.w3.org/2000/svg";
      const XHTML_NS = "http://www.w3.org/1999/xhtml";
      const SLIDE_WIDTH_PT = 720;
      const SLIDE_HEIGHT_PT = 540;

      function setStatus(message, errors = [], hints = []) {
        statusMessage.textContent = message;
        statusErrors.innerHTML = "";
        statusHints.innerHTML = "";
        for (const error of errors) {
          const li = document.createElement("li");
          li.textContent = error;
          statusErrors.appendChild(li);
        }
        for (const hint of hints) {
          const li = document.createElement("li");
          li.textContent = hint;
          statusHints.appendChild(li);
        }
      }

      function buildDraftCheckSummaryText(summary) {
        if (!summary || typeof summary !== "object") {
          return "";
        }
        const bodySlideCount = Number(summary.body_slide_count || 0);
        const sectionBreakCount = Number(summary.section_break_count || 0);
        const procedureSlideCount = Number(summary.procedure_slide_count || 0);
        if (!bodySlideCount) {
          return "";
        }
        return `Checked ${bodySlideCount} body slide(s): ${sectionBreakCount} section break(s), ${procedureSlideCount} procedure slide(s).`;
      }

      function setDraftCheck(message, errors = [], warnings = [], hints = [], summary = null) {
        const summaryText = buildDraftCheckSummaryText(summary);
        draftCheckMessage.textContent = summaryText ? `${message} ${summaryText}` : message;
        draftCheckErrors.innerHTML = "";
        draftCheckWarnings.innerHTML = "";
        draftCheckHints.innerHTML = "";
        for (const error of errors) {
          const li = document.createElement("li");
          li.textContent = error;
          draftCheckErrors.appendChild(li);
        }
        for (const warning of warnings) {
          const li = document.createElement("li");
          li.textContent = warning;
          draftCheckWarnings.appendChild(li);
        }
        for (const hint of hints) {
          const li = document.createElement("li");
          li.textContent = hint;
          draftCheckHints.appendChild(li);
        }
      }

      function isManualMode() {
        return true;
      }

      function currentTemplateName() {
        return MANUAL_TEMPLATE_NAME;
      }

      function syncManualLayout() {
        const manual = isManualMode();
        styleGallery.hidden = !manual;
        manualRail.hidden = !manual;
        slidePreviewBox.hidden = !manual;
        workspace.classList.toggle("manual-layout", manual);
        if (manual) {
          syncStylePresetUi();
        }
      }

      function getSelectedPreset() {
        if (!selectedPresetId) {
          return null;
        }
        return stylePresetById.get(selectedPresetId) || null;
      }

      function syncStylePresetUi() {
        const familyChips = Array.from(styleFamilyFilters.querySelectorAll("[data-family-filter]"));
        const presetCards = Array.from(stylePresetGrid.querySelectorAll("[data-preset-id]"));

        familyChips.forEach((chip) => {
          const selected = chip.dataset.familyFilter === activeFamilyFilter;
          chip.classList.toggle("is-selected", selected);
          chip.setAttribute("aria-pressed", selected ? "true" : "false");
        });

        const visiblePresetIds = [];
        presetCards.forEach((card) => {
          const visible = activeFamilyFilter === "all" || card.dataset.familyId === activeFamilyFilter;
          card.hidden = !visible;
          if (visible) {
            visiblePresetIds.push(card.dataset.presetId);
          }
        });
        if ((!selectedPresetId || !visiblePresetIds.includes(selectedPresetId)) && visiblePresetIds.length) {
          selectedPresetId = visiblePresetIds[0];
        }
        presetCards.forEach((card) => {
          const selected = !card.hidden && card.dataset.presetId === selectedPresetId;
          card.classList.toggle("is-selected", selected);
          card.setAttribute("aria-pressed", selected ? "true" : "false");
        });

        addSlideButton.disabled = !getSelectedPreset();
      }

      function clearUploadedImageUrls() {
        for (const url of uploadedImageUrls.values()) {
          URL.revokeObjectURL(url);
        }
        uploadedImageUrls = new Map();
      }

      function pruneSelectedFiles() {
        const validRefs = new Set(requiredImages.map((item) => item.ref));
        const next = new Map();
        for (const [ref, file] of selectedFilesByRef.entries()) {
          if (validRefs.has(ref)) {
            next.set(ref, file);
          }
        }
        selectedFilesByRef = next;
        if (activePasteRef && !validRefs.has(activePasteRef)) {
          activePasteRef = null;
        }
      }

      function syncUploadedImageUrls() {
        clearUploadedImageUrls();
        for (const item of requiredImages) {
          const file = selectedFilesByRef.get(item.ref);
          if (file) {
            uploadedImageUrls.set(item.ref, URL.createObjectURL(file));
          }
        }
      }

      function selectedFileCount() {
        return selectedFilesByRef.size;
      }

      function setSelectedFile(ref, file) {
        if (!ref) {
          return;
        }
        if (file) {
          selectedFilesByRef.set(ref, file);
        } else {
          selectedFilesByRef.delete(ref);
        }
        syncUploadedImageUrls();
      }

      function resetUploads() {
        requiredImages = [];
        slidePreviews = [];
        selectedFilesByRef = new Map();
        activePasteRef = null;
        clearUploadedImageUrls();
        renderSlidePreviews();
      }

      function renderSlidePreviews() {
        slidePreviewList.innerHTML = "";
        syncManualLayout();
        if (!isManualMode()) {
          return;
        }
        if (!slidePreviews.length) {
          const li = document.createElement("li");
          li.className = "slide-card";
          li.textContent = "Slide previews appear here after you refresh the manual draft.";
          slidePreviewList.appendChild(li);
          return;
        }

        for (const preview of slidePreviews) {
          const imageBlocks = (preview.image_blocks || []).filter((block) => block.ref);
          const row = document.createElement("li");
          row.className = imageBlocks.length
            ? "slide-preview-row has-upload"
            : "slide-preview-row";
          if (imageBlocks.length) {
            row.appendChild(buildAlignedUploadCard(preview, imageBlocks));
          }
          row.appendChild(buildPreviewCard(preview));
          slidePreviewList.appendChild(row);
        }
      }

      function buildPreviewCard(preview) {
        const card = document.createElement("article");
        card.className = "slide-card";
        card.appendChild(buildSlideCardHead(preview));

        const canvas = document.createElement("div");
        canvas.className = `slide-canvas ${preview.template_name === MANUAL_TEMPLATE_NAME ? "manual" : "editorial"}`;
        canvas.appendChild(buildSlidePreviewSvg(preview));

        card.appendChild(canvas);
        return card;
      }

      function buildAlignedUploadCard(preview, imageBlocks) {
        const card = document.createElement("section");
        card.className = "slide-upload-card";
        card.appendChild(buildSlideCardHead(preview, { showMeta: false, showDelete: false }));
        card.appendChild(buildSlideUploadPanel(preview, imageBlocks));
        return card;
      }

      function buildSlideCardHead(preview, options = {}) {
        const showMeta = options.showMeta !== false;
        const showDelete = options.showDelete !== false;
        const header = document.createElement("div");
        header.className = "slide-card-head";

        const title = document.createElement("div");
        title.className = "slide-card-title";
        title.textContent = buildSlideSummary(preview);
        if (!showMeta) {
          title.title = buildSlideSummary(preview);
        }

        header.appendChild(title);
        const actions = document.createElement("div");
        actions.className = "slide-card-actions";
        let hasActions = false;
        if (showMeta) {
          const meta = document.createElement("div");
          meta.className = "slide-card-meta";
          meta.textContent = preview.continuation
            ? `${preview.pattern_id} | continuation`
            : preview.pattern_id;
          actions.appendChild(meta);
          hasActions = true;
        }
        if (showDelete && shouldRenderDeleteButton(preview)) {
          const deleteButton = document.createElement("button");
          deleteButton.type = "button";
          deleteButton.className = "slide-delete-button";
          deleteButton.textContent = "Delete";
          deleteButton.setAttribute("aria-label", `Delete ${buildSlideSummary(preview)}`);
          deleteButton.dataset.deleteLocked = canDeletePreview(preview) ? "false" : "true";
          deleteButton.disabled = !canDeletePreview(preview);
          deleteButton.addEventListener("click", () => {
            void deleteManualSlide(preview, deleteButton);
          });
          actions.appendChild(deleteButton);
          hasActions = true;
        }
        if (hasActions) {
          header.appendChild(actions);
        }
        return header;
      }

      function buildSlideSummary(preview) {
        return `${preview.slide_no}. ${preview.slide_title}`;
      }

      function canDeletePreview(preview) {
        return Boolean(preview && preview.source_can_delete);
      }

      function shouldRenderDeleteButton(preview) {
        return Boolean(
          preview
          && preview.source_is_primary_preview !== false
          && ["contents_slide", "content_slide"].includes(preview.source_kind)
        );
      }

      function setPreviewDeleteButtonsDisabled(disabled) {
        slidePreviewList.querySelectorAll(".slide-delete-button").forEach((button) => {
          button.disabled = disabled || button.dataset.deleteLocked === "true";
        });
      }

      function buildSlideUploadPanel(preview, imageBlocks) {
        const panel = document.createElement("div");
        panel.className = "slide-upload-panel";

        for (const block of imageBlocks) {
          panel.appendChild(buildSlideUploadSlot(preview, block));
        }

        return panel;
      }

      function buildSlideUploadSlot(preview, block) {
        const slotCard = document.createElement("div");
        slotCard.className = "slide-upload-slot";
        if (activePasteRef === block.ref) {
          slotCard.classList.add("is-active");
        }
        slotCard.tabIndex = 0;

        slotCard.addEventListener("click", () => {
          activePasteRef = block.ref || null;
          slotCard.focus();
        });
        slotCard.addEventListener("focus", () => {
          activePasteRef = block.ref || null;
        });
        slotCard.addEventListener("blur", () => {
          if (activePasteRef === block.ref) {
            activePasteRef = null;
          }
        });
        slotCard.addEventListener("paste", (event) => {
          const pastedFile = extractClipboardImageFile(event.clipboardData, block.ref);
          if (!pastedFile) {
            return;
          }
          event.preventDefault();
          setSelectedFile(block.ref, pastedFile);
          renderSlidePreviews();
          setStatus(
            `Updated ${preview.slide_title}.`,
            [],
            [`${block.ref} was replaced from the clipboard.`]
          );
        });

        const head = document.createElement("div");
        head.className = "slide-upload-slot-head";

        const title = document.createElement("div");
        title.className = "slide-upload-slot-title";
        title.textContent = block.label || block.ref || "Image Slot";

        const state = document.createElement("div");
        state.className = "slide-upload-slot-state";
        state.textContent = selectedFilesByRef.has(block.ref) ? "Ready" : "Waiting";

        head.appendChild(title);
        head.appendChild(state);
        slotCard.appendChild(head);

        const slotCopy = document.createElement("p");
        slotCopy.className = "slide-upload-slot-copy";
        slotCopy.textContent = `Ref ${block.ref}. Click this panel and paste a screenshot, or choose a file below.`;
        slotCard.appendChild(slotCopy);

        const actions = document.createElement("div");
        actions.className = "slide-upload-actions";

        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".png,.jpg,.jpeg";
        input.addEventListener("click", (event) => {
          event.stopPropagation();
          activePasteRef = block.ref || null;
        });
        input.addEventListener("change", () => {
          const file = (input.files || [])[0];
          if (!file) {
            return;
          }
          setSelectedFile(block.ref, file);
          renderSlidePreviews();
          setStatus(
            `Updated ${preview.slide_title}.`,
            [],
            [`${block.ref} now uses ${file.name}.`]
          );
        });
        actions.appendChild(input);

        const clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className = "slide-upload-clear";
        clearButton.textContent = "Clear";
        clearButton.disabled = !selectedFilesByRef.has(block.ref);
        clearButton.addEventListener("click", (event) => {
          event.stopPropagation();
          setSelectedFile(block.ref, null);
          renderSlidePreviews();
          setStatus(
            `Cleared ${block.ref}.`,
            [],
            ["Choose another screenshot or paste from the clipboard when you are ready."]
          );
        });
        actions.appendChild(clearButton);

        slotCard.appendChild(actions);

        const fileName = document.createElement("div");
        fileName.className = "slide-upload-file-name";
        const selected = selectedFilesByRef.get(block.ref);
        fileName.textContent = selected
          ? selected.name
          : "No screenshot selected yet.";
        slotCard.appendChild(fileName);

        return slotCard;
      }

      function extractClipboardImageFile(clipboardData, ref) {
        if (!clipboardData || !clipboardData.items) {
          return null;
        }
        for (const item of clipboardData.items) {
          if (!item.type || !item.type.startsWith("image/")) {
            continue;
          }
          const blob = item.getAsFile();
          if (!blob) {
            continue;
          }
          const extension = item.type === "image/jpeg" ? "jpg" : "png";
          return new File([blob], `${ref || "slide"}-paste.${extension}`, {
            type: item.type,
          });
        }
        return null;
      }

      function buildSlidePreviewSvg(preview) {
        const svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("viewBox", `0 0 ${SLIDE_WIDTH_PT} ${SLIDE_HEIGHT_PT}`);
        svg.setAttribute("class", "slide-svg");
        svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

        const background = document.createElementNS(SVG_NS, "rect");
        background.setAttribute("x", "0");
        background.setAttribute("y", "0");
        background.setAttribute("width", String(SLIDE_WIDTH_PT));
        background.setAttribute("height", String(SLIDE_HEIGHT_PT));
        background.setAttribute("rx", "16");
        background.setAttribute("fill", "#ffffff");
        svg.appendChild(background);

        for (const decoration of preview.decorations || []) {
          svg.appendChild(buildSlideDecorationNode(decoration));
        }
        for (const block of preview.image_blocks || []) {
          svg.appendChild(buildSlideImageNode(block));
        }
        for (const block of preview.text_blocks || []) {
          svg.appendChild(buildSlideTextNode(block));
        }

        return svg;
      }

      function buildSlideDecorationNode(block) {
        const node = document.createElementNS(SVG_NS, "rect");
        node.setAttribute("x", String(toPreviewX(block.x_pct)));
        node.setAttribute("y", String(toPreviewY(block.y_pct)));
        node.setAttribute("width", String(toPreviewWidth(block.w_pct)));
        node.setAttribute("height", String(toPreviewHeight(block.h_pct)));
        node.setAttribute("rx", block.shape_type === "rounded_rectangle" ? "14" : "0");
        node.setAttribute("fill", block.fill_color || "#ffffff");
        if (block.line_color) {
          node.setAttribute("stroke", block.line_color);
          node.setAttribute("stroke-width", "1");
        }
        return node;
      }

      function buildSlideTextNode(block) {
        const node = document.createElementNS(SVG_NS, "foreignObject");
        node.setAttribute("x", String(toPreviewX(block.x_pct)));
        node.setAttribute("y", String(toPreviewY(block.y_pct)));
        node.setAttribute("width", String(toPreviewWidth(block.w_pct)));
        node.setAttribute("height", String(toPreviewHeight(block.h_pct)));

        const shell = document.createElement("div");
        shell.setAttribute("xmlns", XHTML_NS);
        shell.style.width = "100%";
        shell.style.height = "100%";
        shell.style.boxSizing = "border-box";
        shell.style.overflow = "hidden";
        shell.style.padding = block.role === "title" ? "2pt 4pt" : "1pt 3pt";
        shell.style.whiteSpace = "pre-wrap";
        shell.style.wordBreak = "break-word";
        shell.style.color = previewTextColor(block.role);
        shell.style.fontSize = `${previewTextSize(block)}pt`;
        shell.style.fontWeight = previewTextWeight(block.role);
        shell.style.lineHeight = block.role === "meta" ? "1.1" : "1.24";
        shell.style.letterSpacing = block.role === "title" ? "-0.02em" : (block.role === "meta" ? "0.04em" : "0");
        shell.style.textTransform = block.role === "meta" ? "uppercase" : "none";
        shell.style.fontFamily = block.font_name
          ? `"${block.font_name}", "Segoe UI", Arial, sans-serif`
          : `"Segoe UI", Arial, sans-serif`;
        shell.textContent = block.text;

        node.appendChild(shell);
        return node;
      }

      function buildSlideImageNode(block) {
        const node = document.createElementNS(SVG_NS, "foreignObject");
        node.setAttribute("x", String(toPreviewX(block.x_pct)));
        node.setAttribute("y", String(toPreviewY(block.y_pct)));
        node.setAttribute("width", String(toPreviewWidth(block.w_pct)));
        node.setAttribute("height", String(toPreviewHeight(block.h_pct)));

        const shell = document.createElement("div");
        shell.setAttribute("xmlns", XHTML_NS);
        shell.style.width = "100%";
        shell.style.height = "100%";
        shell.style.boxSizing = "border-box";
        shell.style.borderRadius = "12pt";
        shell.style.overflow = "hidden";
        const uploadedUrl = block.ref ? uploadedImageUrls.get(block.ref) : null;
        const hasUploadedImage = Boolean(uploadedUrl);
        shell.style.border = hasUploadedImage
          ? "1px solid rgba(148, 163, 184, 0.35)"
          : "1px dashed rgba(91, 104, 122, 0.45)";
        shell.style.background = hasUploadedImage
          ? "#ffffff"
          : "linear-gradient(180deg, rgba(226,232,240,0.8), rgba(248,250,252,0.98))";
        shell.style.display = "flex";
        shell.style.alignItems = "center";
        shell.style.justifyContent = "center";

        if (uploadedUrl) {
          const image = document.createElement("img");
          image.setAttribute("xmlns", XHTML_NS);
          image.src = uploadedUrl;
          image.alt = block.ref || block.label || "Uploaded preview";
          image.style.width = "100%";
          image.style.height = "100%";
          image.style.objectFit = block.fit === "contain" ? "contain" : "cover";
          image.style.display = "block";
          image.style.background = "#ffffff";
          shell.appendChild(image);
        } else {
          const placeholder = document.createElement("div");
          placeholder.setAttribute("xmlns", XHTML_NS);
          placeholder.style.padding = "10pt";
          placeholder.style.textAlign = "center";
          placeholder.style.color = "#64748b";
          placeholder.style.fontSize = "10pt";
          placeholder.style.lineHeight = "1.3";
          placeholder.style.whiteSpace = "pre-wrap";
          placeholder.textContent = block.ref
            ? `${block.ref}\nUpload to preview this slot.`
            : `${block.label}\nUpload to preview this slot.`;
          shell.appendChild(placeholder);
        }

        node.appendChild(shell);
        return node;
      }

      function previewTextSize(block) {
        if (block.font_size_pt) {
          return block.font_size_pt;
        }
        if (block.role === "title") {
          return 24;
        }
        if (block.role === "meta") {
          return 10;
        }
        if (block.role === "caption") {
          return 10;
        }
        return 14;
      }

      function previewTextWeight(role) {
        if (role === "title") {
          return "800";
        }
        if (role === "meta") {
          return "700";
        }
        return "500";
      }

      function previewTextColor(role) {
        if (role === "meta") {
          return "#0f766e";
        }
        if (role === "caption") {
          return "#64748b";
        }
        return "#0f172a";
      }

      function toPreviewX(percent) {
        return (Number(percent || 0) / 100) * SLIDE_WIDTH_PT;
      }

      function toPreviewY(percent) {
        return (Number(percent || 0) / 100) * SLIDE_HEIGHT_PT;
      }

      function toPreviewWidth(percent) {
        return (Number(percent || 0) / 100) * SLIDE_WIDTH_PT;
      }

      function toPreviewHeight(percent) {
        return (Number(percent || 0) / 100) * SLIDE_HEIGHT_PT;
      }

      async function postPayload(url) {
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        formData.append("built_in", currentTemplateName());
        const imageManifest = isManualMode()
          ? requiredImages.filter((item) => selectedFilesByRef.has(item.ref)).map((item) => ({
              ref: item.ref,
              field_name: item.ref,
              filename: selectedFilesByRef.get(item.ref)?.name || item.ref,
            }))
          : [];
        formData.append("image_manifest", JSON.stringify(imageManifest));
        if (isManualMode()) {
          requiredImages.forEach((item) => {
            const file = selectedFilesByRef.get(item.ref);
            if (file) {
              formData.append(item.ref, file, file.name);
            }
          });
        }
        return fetch(url, { method: "POST", body: formData });
      }

      async function postManualSlideStyle() {
        const preset = getSelectedPreset();
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        formData.append("built_in", currentTemplateName());
        if (preset && preset.preset_id) {
          formData.append("preset_id", preset.preset_id);
        }
        return fetch("/api/manual-slide-style", { method: "POST", body: formData });
      }

      async function postManualSlideDelete(preview) {
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        formData.append("built_in", currentTemplateName());
        formData.append("source_kind", preview.source_kind || "");
        if (Number.isInteger(preview.source_slide_index)) {
          formData.append("source_slide_index", String(preview.source_slide_index));
        }
        return fetch("/api/manual-slide-delete", { method: "POST", body: formData });
      }

      async function postManualDraftCheck() {
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        formData.append("built_in", currentTemplateName());
        return fetch("/api/manual-draft-check", { method: "POST", body: formData });
      }

      async function checkManualDraft(options = {}) {
        if (!payloadNode.value.trim()) {
          const message = "Draft checker failed. Please provide payload YAML.";
          const hints = ["Reset the starter example to begin again."];
          setDraftCheck(message, [message], [], hints);
          if (options.setStatusOnFailure !== false) {
            setStatus(message, [message], hints);
          }
          return { ok: false, errors: [message], warnings: [], hints, summary: null };
        }
        checkDraftButton.disabled = true;
        draftCheckLink.disabled = true;
        try {
          const response = await postManualDraftCheck();
          const payload = await response.json();
          payloadNode.value = payload.payload_yaml || payloadNode.value;
          if (!response.ok) {
            const message = payload.message || "Draft checker failed.";
            const errors = payload.errors || [];
            const hints = payload.hints || [];
            setDraftCheck(message, errors, [], hints);
            if (options.setStatusOnFailure !== false) {
              setStatus(message, errors, hints);
            }
            return { ok: false, errors, warnings: [], hints, summary: null };
          }
          setDraftCheck(
            payload.message || "Draft checker finished.",
            payload.errors || [],
            payload.warnings || [],
            payload.hints || [],
            payload.summary || null,
          );
          if (payload.ok) {
            if (options.setStatusOnPass) {
              setStatus(payload.message || "Draft checker passed.", [], payload.hints || []);
            }
          } else if (options.setStatusOnFailure !== false) {
            setStatus(payload.message || "Draft checker found blocking issues.", payload.errors || [], payload.hints || []);
          }
          return payload;
        } catch (error) {
          const message = "A network error occurred while checking the draft.";
          setDraftCheck(message, [message], [], []);
          if (options.setStatusOnFailure !== false) {
            setStatus(message);
          }
          return { ok: false, errors: [message], warnings: [], hints: [], summary: null };
        } finally {
          checkDraftButton.disabled = false;
          draftCheckLink.disabled = false;
        }
      }

      async function refreshImageOrder(options = {}) {
        if (!isManualMode()) {
          return false;
        }
        if (!payloadNode.value.trim()) {
          setStatus("Manual compile failed. Please provide payload YAML.", [], ["Reset the manual starter example to begin again."]);
          return false;
        }
        const draftCheck = await checkManualDraft({
          setStatusOnPass: false,
          setStatusOnFailure: true,
        });
        if (!draftCheck.ok) {
          requiredImages = [];
          slidePreviews = [];
          clearUploadedImageUrls();
          renderSlidePreviews();
          return false;
        }
        setStatus("Inspecting the manual draft and refreshing the preview rail...");
        const response = await postPayload("/api/compile");
        const payload = await response.json();
        payloadNode.value = payload.payload_yaml || payloadNode.value;
        if (!response.ok) {
          requiredImages = [];
          slidePreviews = [];
          clearUploadedImageUrls();
          renderSlidePreviews();
          setStatus(payload.message || "Compile failed.", payload.errors || [], payload.hints || []);
          return false;
        }
        requiredImages = (payload.required_images || []).map((item, index) => ({
          ...item,
          order: index + 1,
        }));
        slidePreviews = payload.slide_previews || [];
        pruneSelectedFiles();
        syncUploadedImageUrls();
        renderSlidePreviews();
        const successHints = [];
        if (Array.isArray(options.successHints)) {
          successHints.push(...options.successHints);
        }
        if (requiredImages.length) {
          successHints.push(
            `Add ${requiredImages.length} screenshot file(s) in the aligned upload panels.`,
            "Only slides with image slots show upload controls, and each panel stays beside its matching preview.",
          );
        } else {
          successHints.push("No image-backed slides are required for the current manual draft.");
        }
        setStatus(
          options.successMessage || "Manual preview refreshed.",
          [],
          successHints
        );
        return true;
      }

      async function addManualSlideStyle() {
        if (!payloadNode.value.trim()) {
          setStatus("Slide insertion failed. Please provide payload YAML.", [], ["Reset the manual starter example to begin again."]);
          return;
        }
        const selectedPreset = getSelectedPreset();
        if (!selectedPreset) {
          setStatus(
            "Slide insertion failed. Please choose a visible slide preset first.",
            [],
            ["Pick a preset card in the gallery, then try Add Slide again."]
          );
          return;
        }
        const selectedLabel = selectedPreset.label || "manual slide";
        addSlideButton.disabled = true;
        setStatus(`Adding ${selectedLabel} to the manual draft...`);
        try {
          const response = await postManualSlideStyle();
          const payload = await response.json();
          if (!response.ok) {
            setStatus(payload.message || "Slide insertion failed.", payload.errors || [], payload.hints || []);
            return;
          }
          payloadNode.value = payload.payload_yaml || payloadNode.value;
          await refreshImageOrder({
            successMessage: payload.message || `${selectedLabel} added to the manual draft.`,
            successHints: payload.hints || [],
          });
        } catch (error) {
          setStatus("A network error occurred. Please try again in a moment.");
        } finally {
          addSlideButton.disabled = false;
        }
      }

      async function deleteManualSlide(preview, button) {
        if (!canDeletePreview(preview)) {
          return;
        }
        const slideLabel = buildSlideSummary(preview);
        button.disabled = true;
        setPreviewDeleteButtonsDisabled(true);
        setStatus(`Removing ${slideLabel} from the manual draft...`);
        try {
          const response = await postManualSlideDelete(preview);
          const payload = await response.json();
          if (!response.ok) {
            setStatus(payload.message || "Slide deletion failed.", payload.errors || [], payload.hints || []);
            return;
          }
          payloadNode.value = payload.payload_yaml || payloadNode.value;
          await refreshImageOrder({
            successMessage: payload.message || `${slideLabel} removed from the manual draft.`,
            successHints: payload.hints || [],
          });
        } catch (error) {
          setStatus("A network error occurred. Please try again in a moment.");
        } finally {
          setPreviewDeleteButtonsDisabled(false);
          if (button.isConnected) {
            button.disabled = false;
          }
        }
      }

      function applyStarter() {
        payloadNode.value = PROMPTED_MANUAL_PROCEDURE_EXAMPLE;
        resetUploads();
        setStatus(
          "Manual starter loaded.",
          [],
          [
            "The AI prompt comments are back at the top of the manual starter YAML.",
            "Use Check Draft to catch unsupported manual pattern_id values before generating.",
            "Choose a gallery preset and use Add Slide to append more manual steps.",
            "Use Delete on the right preview rail to remove a contents slide or manual step from the current draft.",
            "Reset, Add Slide, and Delete refresh the preview rail automatically, and the right-side link refreshes after manual YAML edits.",
          ]
        );
        void refreshImageOrder();
      }

      applyStarter();

      styleFamilyFilters.addEventListener("click", (event) => {
        const chip = event.target.closest("[data-family-filter]");
        if (!chip) {
          return;
        }
        activeFamilyFilter = chip.dataset.familyFilter || "all";
        syncStylePresetUi();
      });
      stylePresetGrid.addEventListener("click", (event) => {
        const card = event.target.closest("[data-preset-id]");
        if (!card) {
          return;
        }
        selectedPresetId = card.dataset.presetId || selectedPresetId;
        syncStylePresetUi();
      });
      document.getElementById("reset-starter").addEventListener("click", () => {
        applyStarter();
      });
      checkDraftButton.addEventListener("click", () => { void checkManualDraft({ setStatusOnPass: true, setStatusOnFailure: true }); });
      draftCheckLink.addEventListener("click", () => { void checkManualDraft({ setStatusOnPass: true, setStatusOnFailure: true }); });
      refreshPreviewButton.addEventListener("click", () => { void refreshImageOrder(); });
      addSlideButton.addEventListener("click", () => { void addManualSlideStyle(); });

      document.getElementById("generate-button").addEventListener("click", async () => {
        if (!payloadNode.value.trim()) {
          setStatus("Generation failed. Please provide payload YAML.", [], ["Reset the starter example to begin again."]);
          return;
        }
        const draftCheck = await checkManualDraft({
          setStatusOnPass: false,
          setStatusOnFailure: true,
        });
        if (!draftCheck.ok) {
          return;
        }
        if (isManualMode() && !requiredImages.length) {
          const refreshed = await refreshImageOrder();
          if (!refreshed) {
            return;
          }
        }
        if (isManualMode() && selectedFileCount() !== requiredImages.length) {
          setStatus(
            "Generation failed. Manual mode requires one upload for each listed screenshot slot.",
            [],
            [`Expected ${requiredImages.length} file(s) and received ${selectedFileCount()}.`]
          );
          return;
        }
        const button = document.getElementById("generate-button");
        button.disabled = true;
        setStatus("Validating the payload and generating your Autoreport deck...");
        try {
          const response = await postPayload("/api/generate");
          if (!response.ok) {
            const payload = await response.json();
            button.disabled = false;
            setStatus(payload.message || "Generation failed.", payload.errors || [], payload.hints || []);
            return;
          }
          const blob = await response.blob();
          const downloadUrl = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = downloadUrl;
          anchor.download = "autoreport_demo.pptx";
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(downloadUrl);
          button.disabled = false;
          setStatus("Generation complete. Your Autoreport deck download should begin shortly.");
        } catch (error) {
          button.disabled = false;
          setStatus("A network error occurred. Please try again in a moment.");
        }
      });
    </script>
  </body>
    </html>""".replace(
        "__PROMPTED_MANUAL_EXAMPLE_JSON__",
        prompted_manual_example_json,
    ).replace(
        "__MANUAL_TEMPLATE_NAME_JSON__",
        manual_template_name_json,
    ).replace(
        "__STYLE_PRESET_CATALOG_JSON__",
        style_catalog_json,
    ).replace(
        "__DEFAULT_STYLE_PRESET_ID_JSON__",
        json.dumps(default_preset_id),
    ).replace(
        "__STYLE_FAMILY_FILTERS_HTML__",
        family_filters_html,
    ).replace(
        "__STYLE_PRESET_CARDS_HTML__",
        preset_cards_html,
    )


INDEX_HTML = _render_demo_html()


def _cleanup_temp_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _log_result(
    *,
    request_id: str,
    result: str,
    started_at: float,
    error_type: str | None = None,
) -> None:
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    LOGGER.info(
        "request_id=%s result=%s duration_ms=%s error_type=%s",
        request_id,
        result,
        duration_ms,
        error_type or "none",
    )


def _error_response(
    *,
    status_code: int,
    error_type: str,
    message: str,
    errors: list[str] | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {
        "error_type": error_type,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors
    return JSONResponse(status_code=status_code, content=payload)


def _is_public_user_app(request: Request) -> bool:
    return request.app is app


def _authoring_payload_uses_images(authoring_payload) -> bool:
    return any(
        bool(slide.assets.images)
        or (
            slide.layout_request is not None
            and slide.layout_request.kind == "text_image"
        )
        for slide in authoring_payload.slides
    )


def _report_payload_uses_images(compiled_payload) -> bool:
    return any(
        slide.kind == "text_image"
        or slide.image is not None
        or any(override.image is not None for override in slide.slot_overrides.values())
        for slide in compiled_payload.slides
    )


def _resolve_built_in_contract(template_name: str):
    if template_name == MANUAL_PUBLIC_TEMPLATE_NAME:
        return _MANUAL_CONTRACT
    return _EDITORIAL_CONTRACT


def _normalize_public_template_name(raw_value: object) -> str:
    if isinstance(raw_value, str) and raw_value in PUBLIC_WEB_TEMPLATE_NAMES:
        return raw_value
    return PUBLIC_BUILT_IN_TEMPLATE_NAME


def _is_manual_public_template(template_name: str) -> bool:
    return template_name == MANUAL_PUBLIC_TEMPLATE_NAME


def _manual_checker_optional_string(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    return None


def _manual_checker_image_alias_count(slots: dict[str, object]) -> int:
    return sum(
        1
        for alias, raw_value in slots.items()
        if isinstance(alias, str)
        and alias.startswith("image_")
        and _manual_checker_optional_string(raw_value) is not None
    )


def _manual_checker_pattern_suggestion(
    *,
    image_alias_count: int,
) -> str | None:
    return _MANUAL_ALLOWED_PATTERN_BY_IMAGE_COUNT.get(image_alias_count)


def _manual_checker_rule_hints() -> list[str]:
    return [
        "Allowed body pattern_id values: "
        + ", ".join(_MANUAL_ALLOWED_BODY_PATTERN_IDS)
        + ".",
        "Use text.manual.section_break for 0 images and "
        "text_image.manual.procedure.one/two/three for 1/2/3 images.",
        "Use step numbers like 2.1 instead of 2-1 in procedure slides.",
    ]


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
    if not _is_manual_public_template(built_in):
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
    line_index = 0

    while line_index < len(candidate_lines):
        raw_line = candidate_lines[line_index].rstrip()
        stripped_line = raw_line.strip()

        if not stripped_line:
            repaired_lines.append(
                "" if block_scalar_indent is None else " " * block_scalar_indent
            )
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

        if stripped_line == "report_content:":
            repaired_lines.append("report_content:")
            section = None
            slot_context = None
            line_index += 1
            continue

        key_match = _MANUAL_AI_KEY_RE.match(stripped_line)
        if key_match is not None:
            key = key_match.group("key")
            if key in _MANUAL_AI_ROOT_CHILD_KEYS:
                repaired_lines.append(f"  {key}:")
                section = key
                slot_context = None
                line_index += 1
                continue

            if section in {"title_slide", "contents_slide"}:
                if key == "pattern_id":
                    repaired_lines.append(f"    {stripped_line}")
                    line_index += 1
                    continue
                if key == "slots":
                    repaired_lines.append("    slots:")
                    slot_context = section
                    line_index += 1
                    continue
                if _manual_ai_known_slot_key(key, context=slot_context):
                    repaired_lines.append(f"      {stripped_line}")
                    if _MANUAL_AI_BLOCK_SCALAR_RE.search(stripped_line):
                        block_scalar_indent = 8
                    line_index += 1
                    continue
                line_index += 1
                continue

            if section == "slides":
                if key == "slots":
                    repaired_lines.append("      slots:")
                    slot_context = "slide"
                    line_index += 1
                    continue
                if key == "pattern_id":
                    repaired_lines.append(f"    - {stripped_line}")
                    slot_context = "slide"
                    line_index += 1
                    continue
                if _manual_ai_known_slot_key(key, context=slot_context):
                    repaired_lines.append(f"        {stripped_line}")
                    if _MANUAL_AI_BLOCK_SCALAR_RE.search(stripped_line):
                        block_scalar_indent = 10
                    line_index += 1
                    continue
                line_index += 1
                continue

            line_index += 1
            continue

        if section == "slides" and _MANUAL_AI_SLIDE_PATTERN_RE.match(stripped_line):
            repaired_lines.append(f"    {stripped_line}")
            slot_context = "slide"
            line_index += 1
            continue

        line_index += 1

    repaired_yaml = "\n".join(
        [*preserved_prefix_lines, *repaired_lines] if preserved_prefix_lines else repaired_lines
    ).strip()
    return repaired_yaml or None


def _parse_public_payload_yaml(
    payload_yaml: str,
    *,
    built_in: str,
) -> tuple[object, str | None]:
    try:
        return parse_yaml_text(payload_yaml), None
    except yaml.YAMLError as original_exc:
        repaired_yaml = _repair_manual_ai_yaml_indentation(
            payload_yaml,
            built_in=built_in,
        )
        if repaired_yaml is None:
            raise
        try:
            return parse_yaml_text(repaired_yaml), repaired_yaml
        except yaml.YAMLError:
            raise original_exc


def _append_manual_auto_repair_feedback(
    response_payload: dict[str, object],
    *,
    repaired_payload_yaml: str,
) -> dict[str, object]:
    updated_payload = dict(response_payload)
    warnings = list(updated_payload.get("warnings", []))
    if _MANUAL_AI_AUTO_REPAIR_WARNING not in warnings:
        warnings.append(_MANUAL_AI_AUTO_REPAIR_WARNING)
    hints = list(updated_payload.get("hints", []))
    if _MANUAL_AI_AUTO_REPAIR_HINT not in hints:
        hints.append(_MANUAL_AI_AUTO_REPAIR_HINT)
    summary = dict(updated_payload.get("summary", {}) or {})
    summary["warning_count"] = len(warnings)
    updated_payload["warnings"] = warnings
    updated_payload["hints"] = hints
    updated_payload["summary"] = summary
    updated_payload["payload_yaml"] = repaired_payload_yaml
    if not updated_payload.get("errors"):
        updated_payload["message"] = (
            "Draft checker passed with warnings. Review the repaired indentation and rule hints before generating."
        )
    return updated_payload


def _build_manual_draft_check(
    raw_data: object,
    *,
    built_in: str,
) -> dict[str, object]:
    if built_in != MANUAL_PUBLIC_TEMPLATE_NAME:
        raise ValidationError(
            [
                "Manual draft checking is only available when the built-in manual starter is active."
            ]
        )

    base_hints = _manual_checker_rule_hints()
    if not isinstance(raw_data, dict):
        return {
            "ok": False,
            "message": "Draft checker found blocking issues.",
            "errors": [
                "The draft must be a YAML mapping rooted at report_content."
            ],
            "warnings": [],
            "hints": base_hints,
            "summary": {
                "payload_kind": "unknown",
                "body_slide_count": 0,
                "section_break_count": 0,
                "procedure_slide_count": 0,
                "blocking_issue_count": 1,
                "warning_count": 0,
            },
        }

    payload_kind = detect_payload_kind(raw_data)
    if payload_kind != "content":
        return {
            "ok": True,
            "message": (
                "Draft checker skipped strict manual pattern checks because the "
                f"payload kind is '{payload_kind}', not report_content."
            ),
            "errors": [],
            "warnings": [
                "The checker is optimized for report_content drafts generated by another AI."
            ],
            "hints": base_hints,
            "summary": {
                "payload_kind": payload_kind,
                "body_slide_count": 0,
                "section_break_count": 0,
                "procedure_slide_count": 0,
                "blocking_issue_count": 0,
                "warning_count": 1,
            },
        }

    root = raw_data.get("report_content")
    if not isinstance(root, dict):
        root = raw_data

    errors: list[str] = []
    warnings: list[str] = []
    section_break_count = 0
    procedure_slide_count = 0

    title_slide = root.get("title_slide")
    if not isinstance(title_slide, dict):
        errors.append("Field 'title_slide' is required.")
    else:
        title_pattern_id = _manual_checker_optional_string(
            title_slide.get("pattern_id")
        )
        if title_pattern_id != _MANUAL_CONTRACT.title_slide.pattern_id:
            errors.append(
                "Field 'title_slide.pattern_id' must be exactly 'cover.manual'."
            )
        if not isinstance(title_slide.get("slots"), dict):
            errors.append("Field 'title_slide.slots' must be an object.")

    contents_slide = root.get("contents_slide")
    if contents_slide is not None:
        if not isinstance(contents_slide, dict):
            errors.append("Field 'contents_slide' must be an object when present.")
        else:
            contents_pattern_id = _manual_checker_optional_string(
                contents_slide.get("pattern_id")
            )
            if contents_pattern_id != _MANUAL_CONTRACT.contents_slide.pattern_id:
                errors.append(
                    "Field 'contents_slide.pattern_id' must be exactly 'contents.manual' when a contents slide is present."
                )
            if not isinstance(contents_slide.get("slots"), dict):
                errors.append("Field 'contents_slide.slots' must be an object.")

    raw_slides = root.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        errors.append("Field 'slides' must contain at least 1 item.")
        raw_slides = []

    valid_body_pattern_ids = set(_MANUAL_ALLOWED_BODY_PATTERN_IDS)
    for index, raw_slide in enumerate(raw_slides):
        prefix = f"slides[{index}]"
        if not isinstance(raw_slide, dict):
            errors.append(f"Field '{prefix}' must be an object.")
            continue

        slots = raw_slide.get("slots")
        if not isinstance(slots, dict):
            errors.append(f"Field '{prefix}.slots' must be an object.")
            continue

        pattern_id = _manual_checker_optional_string(raw_slide.get("pattern_id"))
        image_alias_count = _manual_checker_image_alias_count(slots)
        suggested_pattern_id = _manual_checker_pattern_suggestion(
            image_alias_count=image_alias_count
        )
        step_no = _manual_checker_optional_string(slots.get("step_no"))
        if step_no is not None and _MANUAL_DASH_STEP_NO_RE.fullmatch(step_no):
            warnings.append(
                f"Field '{prefix}.slots.step_no' uses '{step_no}'. Prefer dotted numbering such as '{step_no.replace('-', '.')}'."
            )

        if pattern_id not in valid_body_pattern_ids:
            close_matches = get_close_matches(
                pattern_id or "",
                list(_MANUAL_ALLOWED_BODY_PATTERN_IDS),
                n=2,
                cutoff=0.45,
            )
            suggestion_parts: list[str] = []
            if suggested_pattern_id is not None:
                suggestion_parts.append(
                    f"For {image_alias_count} image slot(s), use '{suggested_pattern_id}'."
                )
            if close_matches:
                suggestion_parts.append(
                    "Closest matches: "
                    + ", ".join(f"'{match}'" for match in close_matches)
                    + "."
                )
            if pattern_id is None:
                errors.append(
                    f"Field '{prefix}.pattern_id' is required for manual body slides. "
                    + " ".join(suggestion_parts)
                )
            else:
                errors.append(
                    f"Field '{prefix}.pattern_id' uses unsupported manual pattern '{pattern_id}'. "
                    + " ".join(suggestion_parts)
                )
            continue

        if pattern_id == "text.manual.section_break":
            section_break_count += 1
            if image_alias_count > 0:
                errors.append(
                    f"Field '{prefix}.pattern_id' is 'text.manual.section_break', so the slide must not define image_* slots."
                )
            section_no = _manual_checker_optional_string(slots.get("section_no"))
            if section_no is not None and not section_no.endswith("."):
                warnings.append(
                    f"Field '{prefix}.slots.section_no' should usually end with a trailing period, such as '2.'."
                )
            continue

        procedure_slide_count += 1
        expected_pattern_id = _MANUAL_ALLOWED_PATTERN_BY_IMAGE_COUNT.get(
            image_alias_count
        )
        if expected_pattern_id is None:
            errors.append(
                f"Field '{prefix}.pattern_id' is '{pattern_id}', but the manual template supports only 1, 2, or 3 image_* slots on procedure slides."
            )
            continue
        if pattern_id != expected_pattern_id:
            errors.append(
                f"Field '{prefix}.pattern_id' is '{pattern_id}', but this slide defines {image_alias_count} image_* slot(s), so it should use '{expected_pattern_id}'."
            )

    summary = {
        "payload_kind": payload_kind,
        "body_slide_count": len(raw_slides),
        "section_break_count": section_break_count,
        "procedure_slide_count": procedure_slide_count,
        "blocking_issue_count": len(errors),
        "warning_count": len(warnings),
    }
    if errors:
        message = f"Draft checker found {len(errors)} blocking issue(s)."
    elif warnings:
        message = (
            "Draft checker passed with warnings. Review the numbering and rule hints before generating."
        )
    else:
        message = (
            "Draft checker passed. The manual draft matches the supported pattern rules."
        )
    return {
        "ok": not errors,
        "message": message,
        "errors": errors,
        "warnings": warnings,
        "hints": base_hints,
        "summary": summary,
    }


def _collect_missing_uploaded_image_errors(
    raw_data: dict[str, object],
    *,
    contract,
    available_image_refs: set[str],
) -> list[str]:
    payload_kind = detect_payload_kind(raw_data)
    if payload_kind not in {"authoring", "content"}:
        return []

    authoring_payload, _ = materialize_authoring_payload(
        raw_data,
        contract,
        available_image_refs=available_image_refs,
        enforce_image_refs=False,
    )
    errors: list[str] = []
    for slide in authoring_payload.slides:
        for image in slide.assets.images:
            if image.path is not None or image.ref is None:
                continue
            if image.ref not in available_image_refs:
                errors.append(
                    f"Slide {slide.slide_no} needs an uploaded image for ref '{image.ref}'. "
                    "Upload the matching file below before generating, or replace the draft image note with a real file path/ref."
                )
    return errors


def _collect_public_demo_image_errors(
    *,
    template_name: str,
    authoring_payload=None,
    compiled_payload=None,
) -> list[str]:
    if _is_manual_public_template(template_name):
        return []
    if authoring_payload is not None and _authoring_payload_uses_images(authoring_payload):
        return list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS)
    if compiled_payload is not None and _report_payload_uses_images(compiled_payload):
        return list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS)
    return []


def _collect_required_images(authoring_payload) -> list[dict[str, object]]:
    required_images: list[dict[str, object]] = []
    for slide in authoring_payload.slides:
        for index, image in enumerate(slide.assets.images, start=1):
            if image.ref is None:
                continue
            required_images.append(
                {
                    "slide_no": slide.slide_no,
                    "slide_title": _derive_required_image_slide_title(slide),
                    "alias": f"image_{index}",
                    "ref": image.ref,
                }
            )
    return required_images


def _derive_required_image_slide_title(slide) -> str:
    slot_values = getattr(slide, "slot_values", {})
    if (
        isinstance(slot_values, dict)
        and "section_no" in slot_values
        and "section_title" in slot_values
    ):
        return f"{slot_values['section_no'].strip()} {slot_values['section_title'].strip()}".strip()
    if (
        isinstance(slot_values, dict)
        and "step_no" in slot_values
        and "step_title" in slot_values
    ):
        return f"{slot_values['step_no'].strip()} {slot_values['step_title'].strip()}".strip()
    return slide.goal


def _build_slide_previews(
    compiled_payload,
    *,
    template_name: str,
    image_refs: dict[str, Path],
    temp_dir_path: Path | None,
) -> list[dict[str, object]]:
    template_profile = get_built_in_profile(template_name)
    preview_image_refs = _resolve_preview_image_refs(
        compiled_payload,
        image_refs=image_refs,
        temp_dir_path=temp_dir_path,
    )
    fill_plan, _ = build_report_fill_plan(
        compiled_payload,
        template_profile,
        image_refs=preview_image_refs,
    )
    uploaded_refs = set(image_refs)
    ref_by_path = {
        _preview_path_key(path): ref for ref, path in preview_image_refs.items()
    }
    content_slide_count = len(compiled_payload.slides)
    content_slide_index = 0

    slide_previews: list[dict[str, object]] = []
    for index, planned_slide in enumerate(fill_plan.slides, start=1):
        if index == 1:
            source_kind = "title_slide"
            source_slide_index = None
            source_can_delete = False
        elif compiled_payload.contents.enabled and index == 2:
            source_kind = "contents_slide"
            source_slide_index = None
            source_can_delete = True
        else:
            if not planned_slide.continuation:
                content_slide_index += 1
            source_kind = "content_slide"
            source_slide_index = content_slide_index
            source_can_delete = (
                not planned_slide.continuation and content_slide_count > 1
            )
        slide_previews.append(
            {
                "slide_no": index,
                "slide_title": planned_slide.slide_title,
                "kind": planned_slide.kind,
                "pattern_id": planned_slide.pattern_id,
                "template_name": template_name,
                "continuation": planned_slide.continuation,
                "source_kind": source_kind,
                "source_slide_index": source_slide_index,
                "source_can_delete": source_can_delete,
                "source_is_primary_preview": not planned_slide.continuation,
                "decorations": [
                    _serialize_preview_decoration(decoration)
                    for decoration in planned_slide.decorations
                ],
                "text_blocks": [
                    _serialize_preview_text_fill(
                        text_fill,
                        pattern_kind=planned_slide.kind,
                    )
                    for text_fill in planned_slide.text_fills
                    if _resolve_preview_text(text_fill)
                ],
                "image_blocks": [
                    _serialize_preview_image_fill(
                        image_fill,
                        ref=ref_by_path.get(_preview_path_key(image_fill.image_path)),
                        uploaded_refs=uploaded_refs,
                    )
                    for image_fill in planned_slide.image_fills
                ],
            }
        )
    return slide_previews


def _resolve_preview_image_refs(
    compiled_payload,
    *,
    image_refs: dict[str, Path],
    temp_dir_path: Path | None,
) -> dict[str, Path]:
    preview_image_refs = dict(image_refs)
    missing_refs = sorted(
        _collect_preview_image_refs(compiled_payload) - set(preview_image_refs)
    )
    if not missing_refs:
        return preview_image_refs
    if temp_dir_path is None:
        raise ValueError("Preview image temp dir is required for unresolved refs.")
    for ref in missing_refs:
        preview_image_refs[ref] = _write_preview_placeholder_image(
            temp_dir_path,
            ref,
        )
    return preview_image_refs


def _collect_preview_image_refs(compiled_payload) -> set[str]:
    refs: set[str] = set()
    for slide in compiled_payload.slides:
        if slide.image is not None and slide.image.ref:
            refs.add(slide.image.ref)
        for override in slide.slot_overrides.values():
            if override.image is not None and override.image.ref:
                refs.add(override.image.ref)
    return refs


def _write_preview_placeholder_image(temp_dir_path: Path, ref: str) -> Path:
    placeholder_path = temp_dir_path / f"preview-placeholder-{ref}.png"
    if not placeholder_path.exists():
        placeholder_path.write_bytes(PREVIEW_PLACEHOLDER_PNG_BYTES)
    return placeholder_path


def _preview_path_key(path: Path) -> str:
    return str(path.resolve())


def _serialize_preview_decoration(decoration) -> dict[str, object]:
    return {
        "shape_type": decoration.shape_type,
        "fill_color": f"rgb({decoration.fill_rgb[0]}, {decoration.fill_rgb[1]}, {decoration.fill_rgb[2]})",
        "line_color": (
            None
            if decoration.line_rgb is None
            else f"rgb({decoration.line_rgb[0]}, {decoration.line_rgb[1]}, {decoration.line_rgb[2]})"
        ),
        "x_pct": _slot_pct(decoration.x, DEFAULT_SLIDE_WIDTH_EMU),
        "y_pct": _slot_pct(decoration.y, DEFAULT_SLIDE_HEIGHT_EMU),
        "w_pct": _slot_pct(decoration.width, DEFAULT_SLIDE_WIDTH_EMU),
        "h_pct": _slot_pct(decoration.height, DEFAULT_SLIDE_HEIGHT_EMU),
    }


def _serialize_preview_text_fill(text_fill, *, pattern_kind: str) -> dict[str, object]:
    text_value = _resolve_preview_text(text_fill)
    return {
        "slot_name": text_fill.slot.slot_name,
        "role": _preview_text_role(text_fill.slot, pattern_kind),
        "text": text_value,
        "font_size_pt": text_fill.font_size,
        "font_name": text_fill.slot.explicit_font_name,
        "x_pct": _slot_pct(text_fill.slot.x, DEFAULT_SLIDE_WIDTH_EMU),
        "y_pct": _slot_pct(text_fill.slot.y, DEFAULT_SLIDE_HEIGHT_EMU),
        "w_pct": _slot_pct(text_fill.slot.width, DEFAULT_SLIDE_WIDTH_EMU),
        "h_pct": _slot_pct(text_fill.slot.height, DEFAULT_SLIDE_HEIGHT_EMU),
    }


def _resolve_preview_text(text_fill) -> str:
    if text_fill.text is not None:
        return text_fill.text
    return "\n".join(text_fill.items)


def _serialize_preview_image_fill(
    image_fill,
    *,
    ref: str | None,
    uploaded_refs: set[str],
) -> dict[str, object]:
    resolved_ref = ref or image_fill.image_path.name
    return {
        "slot_name": image_fill.slot.slot_name,
        "label": image_fill.slot.alias or image_fill.slot.slot_name,
        "ref": resolved_ref,
        "fit": image_fill.fit,
        "uploaded": resolved_ref in uploaded_refs,
        "x_pct": _slot_pct(image_fill.slot.x, DEFAULT_SLIDE_WIDTH_EMU),
        "y_pct": _slot_pct(image_fill.slot.y, DEFAULT_SLIDE_HEIGHT_EMU),
        "w_pct": _slot_pct(image_fill.slot.width, DEFAULT_SLIDE_WIDTH_EMU),
        "h_pct": _slot_pct(image_fill.slot.height, DEFAULT_SLIDE_HEIGHT_EMU),
    }


def _preview_text_role(slot, pattern_kind: str) -> str:
    if slot.slot_type == "title":
        return "title"
    if slot.slot_type == "caption":
        return "caption"
    if _is_preview_body_slot(slot, pattern_kind):
        return "body"
    if (slot.alias or "") in {
        "section_no",
        "step_no",
        "doc_version",
        "author_or_owner",
        "contents_group_label",
        "command_or_action",
    }:
        return "meta"
    return "text"


def _is_preview_body_slot(slot, pattern_kind: str) -> bool:
    return slot.slot_name.startswith(f"{pattern_kind}.body_")


def _slot_pct(value: int, total: int) -> float:
    return round((value / total) * 100, 3)


@app.get("/", response_class=HTMLResponse)
def demo_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/style-presets")
def style_presets(built_in: str = MANUAL_PUBLIC_TEMPLATE_NAME) -> JSONResponse:
    normalized_built_in = _normalize_public_template_name(built_in)
    return JSONResponse(get_style_preset_catalog(normalized_built_in))


@app.post("/api/manual-draft-check")
async def manual_draft_check(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()

    try:
        form = await request.form()
        payload_yaml = form.get("payload_yaml")
        built_in = _normalize_public_template_name(form.get("built_in"))

        if not isinstance(payload_yaml, str):
            raise ValidationError(["Field 'payload_yaml' is required."])

        raw_data, repaired_payload_yaml = _parse_public_payload_yaml(
            payload_yaml,
            built_in=built_in,
        )
        response_payload = _build_manual_draft_check(
            raw_data,
            built_in=built_in,
        )
        if repaired_payload_yaml is not None:
            response_payload = _append_manual_auto_repair_feedback(
                response_payload,
                repaired_payload_yaml=repaired_payload_yaml,
            )
    except yaml.YAMLError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="yaml_parse_error",
        )
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="validation_error",
        )
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Draft checker failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="internal_error",
        )
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return JSONResponse(response_payload)


@app.post("/api/manual-slide-style")
async def add_manual_slide_style(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()

    try:
        form = await request.form()
        payload_yaml = form.get("payload_yaml")
        preset_id = form.get("preset_id")
        legacy_slide_style = form.get("slide_style")
        built_in = _normalize_public_template_name(form.get("built_in"))

        if not isinstance(payload_yaml, str):
            raise ValidationError(["Field 'payload_yaml' is required."])
        if not isinstance(preset_id, str) and not isinstance(legacy_slide_style, str):
            raise ValidationError(
                ["Field 'preset_id' is required."]
            )

        updated_yaml, added_slide, hints = append_style_preset_to_payload_yaml(
            payload_yaml,
            built_in=built_in,
            preset_id=preset_id if isinstance(preset_id, str) else None,
            legacy_slide_style=(
                legacy_slide_style if isinstance(legacy_slide_style, str) else None
            ),
        )
    except yaml.YAMLError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="yaml_parse_error",
        )
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="validation_error",
        )
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Slide insertion failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="internal_error",
        )
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return JSONResponse(
        {
            "payload_yaml": updated_yaml,
            "added_slide": added_slide,
            "hints": hints,
            "message": f"Added {added_slide['slide_title']} to the manual draft.",
        }
    )


@app.post("/api/manual-slide-delete")
async def delete_manual_slide(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()

    try:
        form = await request.form()
        payload_yaml = form.get("payload_yaml")
        source_kind = form.get("source_kind")
        raw_source_slide_index = form.get("source_slide_index")
        built_in = _normalize_public_template_name(form.get("built_in"))

        if not isinstance(payload_yaml, str):
            raise ValidationError(["Field 'payload_yaml' is required."])
        if not isinstance(source_kind, str):
            raise ValidationError(["Field 'source_kind' is required."])

        source_slide_index: int | None = None
        if raw_source_slide_index is not None:
            if not isinstance(raw_source_slide_index, str):
                raise ValidationError(
                    ["Field 'source_slide_index' must be an integer."]
                )
            try:
                source_slide_index = int(raw_source_slide_index)
            except ValueError as exc:
                raise ValidationError(
                    ["Field 'source_slide_index' must be an integer."]
                ) from exc

        updated_yaml, deleted_slide, hints = delete_manual_slide_from_payload_yaml(
            payload_yaml,
            built_in=built_in,
            source_kind=source_kind,
            source_slide_index=source_slide_index,
        )
    except yaml.YAMLError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="yaml_parse_error",
        )
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="validation_error",
        )
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Slide deletion failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="internal_error",
        )
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return JSONResponse(
        {
            "payload_yaml": updated_yaml,
            "deleted_slide": deleted_slide,
            "hints": hints,
            "message": f"Removed {deleted_slide['slide_title']} from the manual draft.",
        }
    )


@app.post("/api/compile")
async def compile_demo_payload(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        (
            raw_data,
            image_refs,
            temp_dir_path,
            built_in,
            repaired_payload_yaml,
        ) = await _parse_request_payload(request, keep_temp_dir=True)
        contract = _resolve_built_in_contract(built_in)
        available_image_refs = image_refs
        payload_kind = detect_payload_kind(raw_data)
        normalized_authoring_yaml: str | None = None
        hints: list[str] = []
        if repaired_payload_yaml is not None:
            hints.append(_MANUAL_AI_AUTO_REPAIR_HINT)
        normalized_authoring = None

        if payload_kind in {"authoring", "content"}:
            normalized_authoring, materialize_hints = materialize_authoring_payload(
                raw_data,
                contract,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            hints.extend(materialize_hints)
            normalized_authoring_yaml = serialize_document(
                normalized_authoring.to_dict(),
                fmt="yaml",
            ).strip()
            compiled_payload = materialize_report_payload(
                normalized_authoring.to_dict(),
                contract,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            if _is_public_user_app(request):
                public_image_errors = _collect_public_demo_image_errors(
                    template_name=built_in,
                    authoring_payload=normalized_authoring,
                )
                if public_image_errors:
                    _log_result(
                        request_id=request_id,
                        result="error",
                        started_at=started_at,
                        error_type="validation_error",
                    )
                    if temp_dir_path is not None:
                        _cleanup_temp_dir(temp_dir_path)
                    return _error_response(
                        status_code=422,
                        error_type="validation_error",
                        message="Payload validation failed.",
                        errors=public_image_errors,
                    )
        else:
            compiled_payload = materialize_report_payload(
                raw_data,
                contract,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            if _is_public_user_app(request):
                public_image_errors = _collect_public_demo_image_errors(
                    template_name=built_in,
                    compiled_payload=compiled_payload,
                )
                if public_image_errors:
                    _log_result(
                        request_id=request_id,
                        result="error",
                        started_at=started_at,
                        error_type="validation_error",
                    )
                    if temp_dir_path is not None:
                        _cleanup_temp_dir(temp_dir_path)
                    return _error_response(
                        status_code=422,
                        error_type="validation_error",
                        message="Payload validation failed.",
                        errors=public_image_errors,
                    )
    except yaml.YAMLError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="yaml_parse_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Payload validation failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="internal_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    response_payload = {
        "payload_kind": payload_kind,
        "normalized_authoring_yaml": normalized_authoring_yaml,
        "payload_yaml": repaired_payload_yaml,
        "compiled_yaml": serialize_document(compiled_payload.to_dict(), fmt="yaml").strip(),
        "slide_count": len(compiled_payload.slides),
        "required_images": (
            []
            if normalized_authoring is None
            else _collect_required_images(normalized_authoring)
        ),
        "slide_previews": _build_slide_previews(
            compiled_payload,
            template_name=built_in,
            image_refs=available_image_refs,
            temp_dir_path=temp_dir_path,
        ),
        "hints": hints,
    }
    if temp_dir_path is not None:
        _cleanup_temp_dir(temp_dir_path)
    return JSONResponse(response_payload)


@app.post("/api/generate", response_model=None)
async def generate_demo_report(request: Request) -> FileResponse | JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        (
            raw_data,
            image_refs,
            temp_dir_path,
            built_in,
            _repaired_payload_yaml,
        ) = await _parse_request_payload(request, keep_temp_dir=True)
        contract = _resolve_built_in_contract(built_in)
        available_image_refs = image_refs
        payload_kind = detect_payload_kind(raw_data)
        if _is_public_user_app(request):
            if payload_kind in {"authoring", "content"}:
                normalized_authoring, _ = materialize_authoring_payload(
                    raw_data,
                    contract,
                    available_image_refs=available_image_refs.keys(),
                    enforce_image_refs=False,
                )
                public_image_errors = _collect_public_demo_image_errors(
                    template_name=built_in,
                    authoring_payload=normalized_authoring,
                )
            else:
                compiled_payload = materialize_report_payload(
                    raw_data,
                    contract,
                    available_image_refs=available_image_refs.keys(),
                    enforce_image_refs=False,
                )
                public_image_errors = _collect_public_demo_image_errors(
                    template_name=built_in,
                    compiled_payload=compiled_payload,
                )
            if public_image_errors:
                _log_result(
                    request_id=request_id,
                    result="error",
                    started_at=started_at,
                    error_type="validation_error",
                )
                _cleanup_temp_dir(temp_dir_path)
                return _error_response(
                    status_code=422,
                    error_type="validation_error",
                    message="Payload validation failed.",
                    errors=public_image_errors,
                )
        missing_image_errors = _collect_missing_uploaded_image_errors(
            raw_data,
            contract=contract,
            available_image_refs=set(available_image_refs.keys()),
        )
        if missing_image_errors:
            _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
            _cleanup_temp_dir(temp_dir_path)
            return _error_response(
                status_code=422,
                error_type="validation_error",
                message="Payload validation failed.",
                errors=missing_image_errors,
            )
        output_path = temp_dir_path / "autoreport_demo.pptx"
        generated_path = generate_report_from_mapping(
            raw_data,
            output_path=output_path,
            template_name=built_in,
            image_refs=available_image_refs,
        )
    except yaml.YAMLError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="yaml_parse_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Payload validation failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="internal_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return FileResponse(
        path=generated_path,
        media_type=MEDIA_TYPE_PPTX,
        filename="autoreport_demo.pptx",
        background=BackgroundTask(_cleanup_temp_dir, temp_dir_path),
    )


async def _parse_request_payload(
    request: Request,
    *,
    keep_temp_dir: bool = False,
) -> tuple[dict[str, object], dict[str, Path], Path | None, str, str | None]:
    form = await request.form()
    uploads = _collect_form_uploads(form)
    payload_yaml = form.get("payload_yaml")
    image_manifest_raw = form.get("image_manifest", "[]")
    built_in = _normalize_public_template_name(form.get("built_in"))
    temp_dir_path: Path | None = None
    try:
        if not isinstance(payload_yaml, str):
            raise ValidationError(["Field 'payload_yaml' is required."])
        if not isinstance(image_manifest_raw, str):
            image_manifest_raw = "[]"

        try:
            image_manifest = json.loads(image_manifest_raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                ["Field 'image_manifest' must be a valid JSON list."]
            ) from exc
        if not isinstance(image_manifest, list):
            raise ValidationError(["Field 'image_manifest' must be a JSON list."])
        if (
            _is_public_user_app(request)
            and image_manifest
            and not _is_manual_public_template(built_in)
        ):
            raise ValidationError(list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS))

        temp_dir_path = Path(tempfile.mkdtemp(prefix="autoreport-web-"))
        image_refs = await _collect_uploaded_images(
            form=form,
            image_manifest=image_manifest,
            temp_dir_path=temp_dir_path,
        )
        raw_data, repaired_payload_yaml = _parse_public_payload_yaml(
            payload_yaml,
            built_in=built_in,
        )

        if keep_temp_dir:
            return raw_data, image_refs, temp_dir_path, built_in, repaired_payload_yaml

        _cleanup_temp_dir(temp_dir_path)
        temp_dir_path = None
        return raw_data, image_refs, None, built_in, repaired_payload_yaml
    except Exception:
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        raise
    finally:
        await _close_form_uploads(uploads)


async def _collect_uploaded_images(
    *,
    form,
    image_manifest: list[object],
    temp_dir_path: Path,
) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    used_refs: set[str] = set()
    temp_dir_root = temp_dir_path.resolve()
    for index, item in enumerate(image_manifest):
        if not isinstance(item, dict):
            raise ValidationError(
                [f"Field 'image_manifest[{index}]' must be an object."]
            )
        ref = item.get("ref")
        field_name = item.get("field_name")
        if not isinstance(ref, str) or not ref.strip():
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' must be a non-empty string."]
            )
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValidationError(
                [f"Field 'image_manifest[{index}].field_name' must be a non-empty string."]
            )
        normalized_ref = _normalize_upload_ref(ref, index=index)
        normalized_field_name = field_name.strip()
        if normalized_ref in used_refs:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' must be unique."]
            )
        upload = form.get(normalized_field_name)
        if not (hasattr(upload, "filename") and hasattr(upload, "read")):
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' does not match an uploaded file."]
            )
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_UPLOAD_SUFFIXES:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' has an unsupported file type."]
            )
        target_path = (temp_dir_path / f"{normalized_ref}{suffix}").resolve()
        try:
            target_path.relative_to(temp_dir_root)
        except ValueError as exc:
            raise ValidationError(
                [
                    f"Field 'image_manifest[{index}].ref' must not contain path separators."
                ]
            ) from exc
        content = await upload.read()
        target_path.write_bytes(content)
        refs[normalized_ref] = target_path
        used_refs.add(normalized_ref)
    return refs


def _collect_form_uploads(form) -> list[object]:
    uploads: list[object] = []
    seen_ids: set[int] = set()
    for _, value in form.multi_items():
        if not _is_upload_value(value):
            continue
        value_id = id(value)
        if value_id in seen_ids:
            continue
        uploads.append(value)
        seen_ids.add(value_id)
    return uploads


async def _close_form_uploads(uploads: list[object]) -> None:
    for upload in uploads:
        close = getattr(upload, "close", None)
        if not callable(close):
            continue
        result = close()
        if hasattr(result, "__await__"):
            await result


def _is_upload_value(value: object) -> bool:
    return (
        hasattr(value, "filename")
        and hasattr(value, "read")
        and hasattr(value, "close")
    )


def _normalize_upload_ref(ref: str, *, index: int) -> str:
    normalized_ref = ref.strip()
    if normalized_ref in {".", ".."} or Path(normalized_ref).name != normalized_ref:
        raise ValidationError(
            [
                f"Field 'image_manifest[{index}].ref' must not contain path separators."
            ]
        )
    return normalized_ref
