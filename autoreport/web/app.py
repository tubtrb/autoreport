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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.background import BackgroundTask

from autoreport.engine.generator import generate_report_from_mapping
from autoreport.loader import parse_yaml_text
from autoreport.template_flow import (
    get_built_in_contract,
    scaffold_payload,
    serialize_document,
)
from autoreport.validator import ValidationError


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg"}

_BUILT_IN_CONTRACT = get_built_in_contract()
DEFAULT_CONTRACT_YAML = serialize_document(_BUILT_IN_CONTRACT.to_dict(), fmt="yaml").strip()
_WEB_EXAMPLE_PAYLOAD = scaffold_payload(_BUILT_IN_CONTRACT)
_WEB_EXAMPLE_PAYLOAD.slides = [
    slide for slide in _WEB_EXAMPLE_PAYLOAD.slides if slide.kind != "text_image"
]
DEFAULT_PAYLOAD_YAML = serialize_document(
    _WEB_EXAMPLE_PAYLOAD.to_dict(),
    fmt="yaml",
).strip()

app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_demo_html() -> str:
    contract_json = json.dumps(DEFAULT_CONTRACT_YAML)
    payload_json = json.dumps(DEFAULT_PAYLOAD_YAML)
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autoreport Demo</title>
    <style>
      :root {
        --bg: #f6f4ef;
        --surface: #ffffff;
        --panel: #f8fafc;
        --text: #1e293b;
        --muted: #64748b;
        --accent: #0f5f49;
        --accent-soft: #e7f7f0;
        --border: #d9e2ec;
        --shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top right, rgba(15,95,73,0.08), transparent 24%),
          linear-gradient(180deg, rgba(15,95,73,0.04), transparent 30%),
          var(--bg);
        color: var(--text);
        font-family: "Segoe UI", Arial, sans-serif;
      }
      main {
        max-width: 1220px;
        margin: 0 auto;
        padding: 42px 18px 54px;
      }
      h1 {
        margin: 0 0 12px;
        text-align: center;
        color: var(--accent);
        font-size: clamp(2rem, 4vw, 3.4rem);
        letter-spacing: -0.04em;
      }
      .hero-copy {
        max-width: 860px;
        margin: 0 auto 28px;
        text-align: center;
        color: var(--muted);
        line-height: 1.7;
      }
      .card {
        background: var(--surface);
        border: 1px solid rgba(15,23,42,0.06);
        border-radius: 24px;
        box-shadow: var(--shadow);
        padding: 24px;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 22px;
      }
      .panel {
        min-width: 0;
      }
      .panel h2 {
        margin: 0 0 10px;
        font-size: 1rem;
      }
      textarea {
        width: 100%;
        min-height: 320px;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        background: var(--panel);
        color: var(--text);
        font: 0.92rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      textarea[readonly] {
        opacity: 0.92;
      }
      .controls {
        display: grid;
        grid-template-columns: 1fr 280px;
        gap: 22px;
        margin-top: 22px;
      }
      .upload-box, .status-box {
        border: 1px solid var(--border);
        border-radius: 18px;
        background: var(--panel);
        padding: 18px;
      }
      .upload-list {
        margin: 12px 0 0;
        padding-left: 18px;
        color: var(--muted);
        line-height: 1.6;
      }
      .actions {
        display: flex;
        gap: 10px;
        margin-top: 14px;
      }
      button {
        border: none;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      .ghost {
        background: var(--accent-soft);
        color: var(--accent);
      }
      .primary {
        width: 100%;
        padding: 14px 18px;
        border-radius: 16px;
        background: var(--accent);
        color: #fff;
      }
      .status-box h3 {
        margin: 0 0 10px;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
      }
      .status-message {
        line-height: 1.7;
        color: var(--text);
      }
      .status-errors {
        margin: 10px 0 0;
        padding-left: 18px;
        color: #b91c1c;
      }
      .footnote {
        margin-top: 18px;
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.6;
      }
      @media (max-width: 980px) {
        .grid, .controls { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Inspect the contract, fill the payload, and generate an Autoreport deck.</h1>
      <p class="hero-copy">
        This demo exposes the built-in editorial template contract, lets you edit the
        matching payload YAML, and supports image uploads through <code>image_1</code>-style
        references for text-image slides.
      </p>
      <section class="card">
        <div class="grid">
          <div class="panel">
            <h2>Template Contract</h2>
            <textarea id="template-contract" readonly aria-label="Template contract"></textarea>
          </div>
          <div class="panel">
            <h2>Report Payload</h2>
            <textarea id="payload-yaml" aria-label="Report payload"></textarea>
            <div class="actions">
              <button id="load-example" class="ghost" type="button">Load Example</button>
            </div>
          </div>
        </div>
        <div class="controls">
          <div class="upload-box">
            <h2>Image Uploads</h2>
            <p class="hero-copy" style="text-align:left; margin:0 0 10px; max-width:none;">
              Upload images, note the generated refs, and place them under
              <code>slides[*].image.ref</code>.
            </p>
            <input id="image-files" type="file" multiple accept=".png,.jpg,.jpeg">
            <ul id="upload-list" class="upload-list"></ul>
          </div>
          <div class="status-box">
            <h3>Current Status</h3>
            <div id="status-message" class="status-message">
              The built-in editorial contract is loaded. Review the payload or upload images and generate the deck.
            </div>
            <ul id="status-errors" class="status-errors"></ul>
            <div class="actions" style="margin-top:16px;">
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
            <p class="footnote">
              Current scope: built-in editorial template, contract-first payload editing, uploaded image refs, instant download.
            </p>
          </div>
        </div>
      </section>
      <p class="footnote" style="text-align:center;">
        Autoreport Public Demo - Submitted payloads are not retained, and generated PPTX files are cleaned up after download.
      </p>
    </main>
    <script>
      const CONTRACT_YAML = __CONTRACT_JSON__;
      const EXAMPLE_PAYLOAD = __PAYLOAD_JSON__;
      const contractNode = document.getElementById("template-contract");
      const payloadNode = document.getElementById("payload-yaml");
      const fileInput = document.getElementById("image-files");
      const uploadList = document.getElementById("upload-list");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const loadExampleButton = document.getElementById("load-example");
      const generateButton = document.getElementById("generate-button");

      let uploadedRefs = [];

      function renderUploads() {
        uploadList.innerHTML = "";
        if (!uploadedRefs.length) {
          const li = document.createElement("li");
          li.textContent = "No uploaded files yet.";
          uploadList.appendChild(li);
          return;
        }
        for (const item of uploadedRefs) {
          const li = document.createElement("li");
          li.textContent = `${item.ref}: ${item.file.name}`;
          uploadList.appendChild(li);
        }
      }

      function setStatus(message, errors = []) {
        statusMessage.textContent = message;
        statusErrors.innerHTML = "";
        for (const error of errors) {
          const li = document.createElement("li");
          li.textContent = error;
          statusErrors.appendChild(li);
        }
      }

      contractNode.value = CONTRACT_YAML;
      payloadNode.value = EXAMPLE_PAYLOAD;
      renderUploads();

      loadExampleButton.addEventListener("click", () => {
        payloadNode.value = EXAMPLE_PAYLOAD;
        setStatus("Starter payload restored. You can edit it directly or upload images for image refs.");
      });

      fileInput.addEventListener("change", () => {
        uploadedRefs = Array.from(fileInput.files || []).map((file, index) => ({
          ref: `image_${index + 1}`,
          file,
        }));
        renderUploads();
        if (uploadedRefs.length) {
          setStatus("Uploads are ready. Reference them from the payload with image_1, image_2, and so on.");
        } else {
          setStatus("No uploads selected.");
        }
      });

      generateButton.addEventListener("click", async () => {
        const payloadYaml = payloadNode.value.trim();
        if (!payloadYaml) {
          setStatus("Generation failed. Please provide payload YAML.");
          return;
        }

        generateButton.disabled = true;
        setStatus("Validating the payload and generating your Autoreport deck...");

        try {
          const formData = new FormData();
          formData.append("payload_yaml", payloadYaml);
          const manifest = uploadedRefs.map((item) => ({
            ref: item.ref,
            field_name: item.ref,
            filename: item.file.name,
          }));
          formData.append("image_manifest", JSON.stringify(manifest));
          for (const item of uploadedRefs) {
            formData.append(item.ref, item.file, item.file.name);
          }

          const response = await fetch("/api/generate", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const payload = await response.json();
            generateButton.disabled = false;
            setStatus(payload.message || "Generation failed.", payload.errors || []);
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
          generateButton.disabled = false;
          setStatus("Generation complete. Your Autoreport deck download should begin shortly.");
        } catch (error) {
          generateButton.disabled = false;
          setStatus("A network error occurred. Please try again in a moment.");
        }
      });
    </script>
  </body>
</html>""".replace("__CONTRACT_JSON__", contract_json).replace("__PAYLOAD_JSON__", payload_json)


INDEX_HTML = _render_demo_html()


def _cleanup_temp_dir(path: Path) -> None:
    """Delete temporary output artifacts after the response is sent."""

    shutil.rmtree(path, ignore_errors=True)


def _log_result(
    *,
    request_id: str,
    result: str,
    started_at: float,
    error_type: str | None = None,
) -> None:
    """Write structured request outcome logs without persisting payload content."""

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


@app.get("/", response_class=HTMLResponse)
def demo_page() -> HTMLResponse:
    """Serve the public demo page."""

    return HTMLResponse(INDEX_HTML)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    """Return a lightweight health response for deployment checks."""

    return {"status": "ok"}


@app.post("/api/generate", response_model=None)
async def generate_demo_report(request: Request) -> FileResponse | JSONResponse:
    """Generate an Autoreport PPTX from payload YAML plus optional uploads."""

    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        form = await request.form()
        payload_yaml = form.get("payload_yaml")
        image_manifest_raw = form.get("image_manifest", "[]")
        if not isinstance(payload_yaml, str):
            return _error_response(
                status_code=422,
                error_type="validation_error",
                message="Payload validation failed.",
                errors=["Field 'payload_yaml' is required."],
            )
        if not isinstance(image_manifest_raw, str):
            image_manifest_raw = "[]"

        image_manifest = json.loads(image_manifest_raw)
        if not isinstance(image_manifest, list):
            raise ValidationError(["Field 'image_manifest' must be a JSON list."])

        temp_dir_path = Path(tempfile.mkdtemp(prefix="autoreport-web-"))
        image_refs = await _collect_uploaded_images(
            form=form,
            image_manifest=image_manifest,
            temp_dir_path=temp_dir_path,
        )

        raw_data = parse_yaml_text(payload_yaml)
        output_path = temp_dir_path / "autoreport_demo.pptx"
        generated_path = generate_report_from_mapping(
            raw_data,
            output_path=output_path,
            image_refs=image_refs,
        )
    except yaml.YAMLError as exc:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="yaml_parse_error",
        )
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
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
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Payload validation failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(
            request_id=request_id,
            result="error",
            started_at=started_at,
            error_type="internal_error",
        )
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(
        request_id=request_id,
        result="success",
        started_at=started_at,
    )
    return FileResponse(
        path=generated_path,
        media_type=MEDIA_TYPE_PPTX,
        filename="autoreport_demo.pptx",
        background=BackgroundTask(_cleanup_temp_dir, temp_dir_path),
    )


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
        if not (
            hasattr(upload, "filename")
            and hasattr(upload, "read")
        ):
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
