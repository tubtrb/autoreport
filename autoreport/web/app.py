"""FastAPI application for the public Autoreport demo."""

from __future__ import annotations

import json
import logging
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
    materialize_authoring_payload,
    detect_payload_kind,
    get_built_in_contract,
    materialize_report_payload,
    serialize_document,
)
from autoreport.validator import ValidationError


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg"}
PUBLIC_WEB_IMAGE_DISABLED_ERRORS = [
    "The public web demo currently supports text and metrics slides only.",
    "Remove text_image patterns and image_* slots, or use the debug app or CLI for image-backed decks.",
]

_BUILT_IN_CONTRACT = get_built_in_contract()
AI_DRAFT_PROMPT_YAML = """
# Paste this brief into another AI and ask it to fill the report_content draft below.
# Goal: draft slide-ready content for Autoreport. The app will normalize report_content
# into authoring_payload and then compile the runtime report_payload automatically.
# How Autoreport uses this draft:
# - Each item in report_content.slides becomes one deck slide.
# - The number of slide entries is the number of content slides in the deck.
# - pattern_id selects the PPT layout pattern, so it must come from template_contract.
# - In report_content, kind is optional when pattern_id already matches template_contract.
# - slots.title / slots.body_1 / slots.image_* / slots.caption_* map to template placeholders.
# Rules for the other AI:
# 1. Return the final answer as one fenced ```yaml code block.
# 2. Inside that code block, keep the top-level key as report_content.
# 3. Do not write any prose before or after the fenced YAML block.
# 4. Do not open a second code block and do not split the YAML across plain text and code.
# 5. Do not declare the total slide count anywhere. Autoreport infers it from slides[*].
# 6. Choose pattern_id values from the template contract.
# 7. Put narrative text into slots.body_1.
# 8. In the public web demo, stay with text.editorial or metrics.editorial slides.
# 9. Do not add slots.image_* or caption_* fields in this public-web draft.
# 10. If a deck truly needs visuals, switch that draft to the debug app or CLI path.
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Replace with the deck title
      subtitle_1: |
        Replace with a concise subtitle
  contents_slide:
    pattern_id: contents.editorial
    slots:
      title: Contents
      body_1: |
        1. Add the first section title
        2. Add the second section title
  slides:
    - pattern_id: text.editorial
      slots:
        title: First section title
        body_1: |
          Write the main narrative for this slide.
""".strip()
WEBSITE_INTRO_EXAMPLE_YAML = f"""
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Autoreport Website Quick Manual
      subtitle_1: |
        Text-first starter flow for the public web demo
  contents_slide:
    pattern_id: contents.editorial
    slots:
      title: Contents
      body_1: |
        1. Published Guide And Updates Routes
        2. Edit The Starter Deck YAML
        3. Generate The Deck
  slides:
    - pattern_id: text.editorial
      slots:
        title: Published Guide And Updates Routes
        body_1: |
          When the release docs are published, the main reader routes are Home
          `/`, User Guide `/guide/`, and the Updates hub under
          `/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`.
          This starter deck keeps the faster in-app walkthrough inside the main
          editor so users can learn the browser flow and generate immediately.
    - pattern_id: text.editorial
      slots:
        title: Edit The Starter Deck YAML
        body_1: |
          The main editor already includes the AI prompt comments and this
          starter manual YAML in one place. Edit the titles and body text
          directly, keep the draft text-first, and use Reset Starter Example to
          restore the packaged manual.
    - pattern_id: metrics.editorial
      slots:
        title: Generate The Deck
        body_1: |
          Default flow: edit the starter YAML
          Supported slide kinds: text.editorial and metrics.editorial
          Image-backed decks: move them to the debug app or CLI
          Output: generate an editable PowerPoint deck
""".strip()
AI_DRAFT_PROMPT_HEADER = AI_DRAFT_PROMPT_YAML.partition("\nreport_content:")[0].strip()
PROMPTED_WEBSITE_INTRO_EXAMPLE_YAML = (
    f"{AI_DRAFT_PROMPT_HEADER}\n{WEBSITE_INTRO_EXAMPLE_YAML}"
).strip()
app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_demo_html() -> str:
    prompted_intro_example_json = json.dumps(PROMPTED_WEBSITE_INTRO_EXAMPLE_YAML)
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
      main { max-width: 1420px; margin: 0 auto; padding: 36px 24px 56px; }
      h1 { margin: 0 0 12px; text-align: center; color: var(--accent); font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -0.04em; }
      .hero-copy { max-width: 880px; margin: 0 auto 28px; text-align: center; color: var(--muted); line-height: 1.7; }
      .card { background: var(--surface); border: 1px solid rgba(15,23,42,0.06); border-radius: 24px; box-shadow: var(--shadow); padding: 28px; }
      .workspace { display: grid; grid-template-columns: minmax(760px, 1.6fr) 340px; gap: 20px; align-items: start; }
      .panel, .rail-box { min-width: 0; }
      .rail { display: grid; gap: 16px; align-self: start; position: sticky; top: 20px; }
      .panel h2, .rail-box h2 { margin: 0 0 8px; font-size: 1rem; }
      .panel-copy, .footnote { color: var(--muted); line-height: 1.6; font-size: 0.95rem; }
      textarea {
        width: 100%;
        min-height: 420px;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        background: var(--panel);
        color: var(--text);
        font: 0.9rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      textarea[readonly] { opacity: 0.94; }
      .primary-actions, .mini-actions { display: grid; gap: 10px; }
      .primary-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 16px; }
      button {
        border: none;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      .ghost { background: var(--accent-soft); color: var(--accent); }
      .primary { width: 100%; padding: 14px 18px; border-radius: 16px; background: var(--accent); color: #fff; }
      .rail-box { border: 1px solid var(--border); border-radius: 18px; background: var(--panel); padding: 18px; }
      .status-errors, .status-hints, .howto-list { margin: 12px 0 0; padding-left: 18px; line-height: 1.6; }
      .howto-list { color: var(--muted); }
      .status-errors { color: #b91c1c; }
      .status-hints { color: var(--accent); }
      code { font-family: "Cascadia Mono", Consolas, monospace; }
      @media (max-width: 1240px) {
        .workspace { grid-template-columns: 1fr; }
        .rail { position: static; }
      }
      @media (max-width: 980px) {
        .primary-actions { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Edit the starter deck and generate an Autoreport PPTX.</h1>
      <p class="hero-copy">
        Start from the built-in website manual below. The public demo is now
        text-first, so the flow stays simple: edit the starter YAML, keep the
        draft to text and metrics slides, and generate the PPTX.
      </p>
      <section class="card">
        <div class="workspace">
          <div class="panel">
            <h2>Starter Deck YAML</h2>
            <p class="panel-copy">
              Start from the built-in website manual below with the AI prompt
              comments at the top. Edit the draft directly, keep the public-web
              flow to <code>text.editorial</code> and
              <code>metrics.editorial</code>, and generate the deck.
            </p>
            <textarea id="payload-yaml" aria-label="Working draft"></textarea>
            <div class="primary-actions">
              <button id="reset-starter" class="ghost" type="button">Reset Starter Example</button>
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
          </div>
          <aside class="rail">
            <div class="rail-box">
              <h2>How To Use</h2>
              <p class="panel-copy">
                This page is intentionally simple. The starter YAML already
                includes the AI prompt and the website manual draft. Edit that
                one block, keep the public flow text-first, and generate the
                deck.
              </p>
              <ul class="howto-list">
                <li>The main editor starts with AI prompt comments and the starter manual draft.</li>
                <li>Edit the starter draft directly in the main editor.</li>
                <li>Keep public-web drafts to <code>text.editorial</code> and <code>metrics.editorial</code>.</li>
                <li>If a deck needs image-backed slides, move that draft to the debug app or CLI.</li>
                <li>Press <code>Generate PPTX</code>.</li>
              </ul>
              <div id="status-message" class="panel-copy">
                The starter manual is loaded with the AI prompt and the text-first
                website walkthrough. Edit the draft and generate the PPTX.
              </div>
              <ul id="status-errors" class="status-errors"></ul>
              <ul id="status-hints" class="status-hints"></ul>
              <p class="footnote">
                Current scope: built-in editorial template, starter manual editing,
                text and metrics slides, and instant PPTX download.
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
    <script>
      const PROMPTED_WEBSITE_INTRO_EXAMPLE = __PROMPTED_INTRO_EXAMPLE_JSON__;
      const payloadNode = document.getElementById("payload-yaml");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const statusHints = document.getElementById("status-hints");

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

      async function postPayload(url) {
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        formData.append("image_manifest", "[]");
        return fetch(url, { method: "POST", body: formData });
      }

      payloadNode.value = PROMPTED_WEBSITE_INTRO_EXAMPLE;

      document.getElementById("reset-starter").addEventListener("click", () => {
        payloadNode.value = PROMPTED_WEBSITE_INTRO_EXAMPLE;
        setStatus(
          "Starter example restored.",
          [],
          [
            "The AI prompt comments are back at the top of the starter YAML.",
            "The built-in website walkthrough is back in the starter YAML.",
            "The public web flow stays on text and metrics slides.",
            "Use the debug app or CLI when a deck needs images."
          ]
        );
      });

      document.getElementById("generate-button").addEventListener("click", async () => {
        if (!payloadNode.value.trim()) {
          setStatus("Generation failed. Please provide payload YAML.", [], ["Reset the starter example to begin again."]);
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
        "__PROMPTED_INTRO_EXAMPLE_JSON__",
        prompted_intro_example_json,
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


def _collect_missing_uploaded_image_errors(
    raw_data: dict[str, object],
    *,
    available_image_refs: set[str],
) -> list[str]:
    payload_kind = detect_payload_kind(raw_data)
    if payload_kind not in {"authoring", "content"}:
        return []

    authoring_payload, _ = materialize_authoring_payload(
        raw_data,
        _BUILT_IN_CONTRACT,
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
    authoring_payload=None,
    compiled_payload=None,
) -> list[str]:
    if authoring_payload is not None and _authoring_payload_uses_images(authoring_payload):
        return list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS)
    if compiled_payload is not None and _report_payload_uses_images(compiled_payload):
        return list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS)
    return []


@app.get("/", response_class=HTMLResponse)
def demo_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/api/compile")
async def compile_demo_payload(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        raw_data, image_refs, temp_dir_path = await _parse_request_payload(request)
        available_image_refs = image_refs
        payload_kind = detect_payload_kind(raw_data)
        normalized_authoring_yaml: str | None = None
        hints: list[str] = []
        normalized_authoring = None

        if payload_kind in {"authoring", "content"}:
            normalized_authoring, hints = materialize_authoring_payload(
                raw_data,
                _BUILT_IN_CONTRACT,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            normalized_authoring_yaml = serialize_document(
                normalized_authoring.to_dict(),
                fmt="yaml",
            ).strip()
            compiled_payload = materialize_report_payload(
                normalized_authoring.to_dict(),
                _BUILT_IN_CONTRACT,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            if _is_public_user_app(request):
                public_image_errors = _collect_public_demo_image_errors(
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
                _BUILT_IN_CONTRACT,
                available_image_refs=available_image_refs.keys(),
                enforce_image_refs=False,
            )
            if _is_public_user_app(request):
                public_image_errors = _collect_public_demo_image_errors(
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
    return JSONResponse(
        {
            "payload_kind": payload_kind,
            "normalized_authoring_yaml": normalized_authoring_yaml,
            "compiled_yaml": serialize_document(compiled_payload.to_dict(), fmt="yaml").strip(),
            "slide_count": len(compiled_payload.slides),
            "hints": hints,
        }
    )


@app.post("/api/generate", response_model=None)
async def generate_demo_report(request: Request) -> FileResponse | JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        raw_data, image_refs, temp_dir_path = await _parse_request_payload(
            request,
            keep_temp_dir=True,
        )
        available_image_refs = image_refs
        payload_kind = detect_payload_kind(raw_data)
        if _is_public_user_app(request):
            if payload_kind in {"authoring", "content"}:
                normalized_authoring, _ = materialize_authoring_payload(
                    raw_data,
                    _BUILT_IN_CONTRACT,
                    available_image_refs=available_image_refs.keys(),
                    enforce_image_refs=False,
                )
                public_image_errors = _collect_public_demo_image_errors(
                    authoring_payload=normalized_authoring,
                )
            else:
                compiled_payload = materialize_report_payload(
                    raw_data,
                    _BUILT_IN_CONTRACT,
                    available_image_refs=available_image_refs.keys(),
                    enforce_image_refs=False,
                )
                public_image_errors = _collect_public_demo_image_errors(
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
) -> tuple[dict[str, object], dict[str, Path], Path | None]:
    form = await request.form()
    payload_yaml = form.get("payload_yaml")
    image_manifest_raw = form.get("image_manifest", "[]")
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
    if _is_public_user_app(request) and image_manifest:
        raise ValidationError(list(PUBLIC_WEB_IMAGE_DISABLED_ERRORS))

    temp_dir_path = Path(tempfile.mkdtemp(prefix="autoreport-web-"))
    image_refs = await _collect_uploaded_images(
        form=form,
        image_manifest=image_manifest,
        temp_dir_path=temp_dir_path,
    )
    raw_data = parse_yaml_text(payload_yaml)

    if keep_temp_dir:
        return raw_data, image_refs, temp_dir_path

    _cleanup_temp_dir(temp_dir_path)
    return raw_data, image_refs, None


async def _collect_uploaded_images(
    *,
    form,
    image_manifest: list[object],
    temp_dir_path: Path,
) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    used_refs: set[str] = set()
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
        if ref in used_refs:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' must be unique."]
            )
        upload = form.get(field_name)
        if not (hasattr(upload, "filename") and hasattr(upload, "read")):
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' does not match an uploaded file."]
            )
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_UPLOAD_SUFFIXES:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' has an unsupported file type."]
            )
        target_path = temp_dir_path / f"{ref}{suffix}"
        content = await upload.read()
        target_path.write_bytes(content)
        refs[ref] = target_path
        used_refs.add(ref)
    return refs
