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
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from autoreport.engine.generator import generate_report_from_mapping
from autoreport.loader import parse_yaml_text
from autoreport.validator import ValidationError


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
DEFAULT_EXAMPLE_YAML = """title: Weekly Business Review
team: Platform Team
week: 2026-W11
highlights:
  - Revenue finished above plan.
  - Customer escalations declined week over week.
metrics:
  tasks_completed: 8
  open_issues: 3
risks:
  - Slide rendering still needs branding polish.
next_steps:
  - Share the generated deck with stakeholders.
"""

app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


class GenerateRequest(BaseModel):
    """JSON payload used by the demo generation endpoint."""

    report_yaml: str


def _render_demo_html() -> str:
    """Build the single-page demo HTML."""

    example_json = json.dumps(DEFAULT_EXAMPLE_YAML.strip())
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autoreport Demo</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #fdfbf7;
        --surface: #ffffff;
        --surface-muted: #f8fafc;
        --text: #1e293b;
        --muted: #64748b;
        --accent: #064e3b;
        --accent-soft: rgba(6, 78, 59, 0.08);
        --border: #e2e8f0;
        --shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
        --error-bg: #fef2f2;
        --error-text: #b91c1c;
        --error-border: #fecaca;
        --success-bg: #ecfdf5;
        --success-text: #065f46;
        --success-border: #bbf7d0;
        --loading-bg: #eff6ff;
        --loading-text: #1d4ed8;
        --loading-border: #bfdbfe;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background:
          linear-gradient(180deg, rgba(6, 78, 59, 0.05) 0%, rgba(6, 78, 59, 0) 28%),
          radial-gradient(circle at top right, rgba(6, 78, 59, 0.08), rgba(6, 78, 59, 0) 30%),
          var(--bg);
        color: var(--text);
        font-family: "Segoe UI", Arial, sans-serif;
      }

      main {
        max-width: 1120px;
        margin: 0 auto;
        padding: 48px 20px 72px;
      }

      .page {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 28px;
      }

      .hero {
        width: 100%;
        text-align: center;
        padding: 8px 12px 0;
      }

      .hero h1 {
        margin: 0 0 14px;
        font-size: clamp(2.1rem, 4vw, 3.6rem);
        line-height: 1.08;
        letter-spacing: -0.04em;
        color: var(--accent);
      }

      .hero p {
        margin: 0 auto;
        max-width: 760px;
        font-size: clamp(1rem, 1.8vw, 1.15rem);
        line-height: 1.75;
        color: var(--muted);
      }

      .hero .subcopy {
        margin-top: 12px;
        max-width: 700px;
        font-size: 0.98rem;
      }

      .main-card {
        width: 100%;
        background: var(--surface);
        border: 1px solid rgba(15, 23, 42, 0.05);
        border-radius: 24px;
        box-shadow: var(--shadow);
        overflow: hidden;
      }

      .main-card-inner {
        display: flex;
        flex-direction: column;
        gap: 28px;
        padding: 24px;
      }

      .editor-layout {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 28px;
      }

      .editor-pane,
      .status-pane {
        min-width: 0;
      }

      .pane-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
      }

      .pane-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.98rem;
        font-weight: 700;
        color: var(--text);
      }

      .pane-title-mark {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 0 6px var(--accent-soft);
      }

      .ghost-button,
      .primary-button {
        border: none;
        cursor: pointer;
        font: inherit;
        transition:
          transform 0.16s ease,
          background-color 0.16s ease,
          color 0.16s ease,
          box-shadow 0.16s ease;
      }

      .ghost-button {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 9px 14px;
        border-radius: 999px;
        background: #ecfdf5;
        color: var(--accent);
        font-size: 0.92rem;
        font-weight: 600;
      }

      .ghost-button:hover {
        background: #d1fae5;
      }

      .primary-button {
        display: flex;
        width: 100%;
        align-items: center;
        justify-content: center;
        gap: 10px;
        padding: 14px 18px;
        border-radius: 16px;
        background: var(--accent);
        color: #ffffff;
        font-size: 1rem;
        font-weight: 700;
        box-shadow: 0 16px 30px rgba(6, 78, 59, 0.26);
      }

      .primary-button:hover {
        background: #047857;
      }

      .primary-button:active,
      .ghost-button:active {
        transform: scale(0.99);
      }

      .primary-button:disabled {
        background: #7aa899;
        cursor: wait;
        box-shadow: none;
      }

      textarea {
        width: 100%;
        min-height: 360px;
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 18px 18px 20px;
        resize: vertical;
        background: var(--surface-muted);
        color: var(--text);
        font: 0.95rem/1.6 "Cascadia Mono", "Consolas", monospace;
        outline: none;
        transition:
          border-color 0.16s ease,
          box-shadow 0.16s ease,
          background-color 0.16s ease;
      }

      textarea:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 4px rgba(6, 78, 59, 0.08);
        background: #ffffff;
      }

      .status-stack {
        display: flex;
        flex-direction: column;
        gap: 18px;
        height: 100%;
      }

      .status-card {
        display: flex;
        flex: 1;
        flex-direction: column;
        justify-content: center;
        gap: 14px;
        min-height: 172px;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid var(--border);
        background: var(--surface-muted);
      }

      .status-label {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--muted);
      }

      .status-panel {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 15px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: #ffffff;
      }

      .status-panel.status-idle {
        border-color: var(--border);
        color: var(--muted);
      }

      .status-panel.status-loading {
        background: var(--loading-bg);
        border-color: var(--loading-border);
        color: var(--loading-text);
      }

      .status-panel.status-success {
        background: var(--success-bg);
        border-color: var(--success-border);
        color: var(--success-text);
      }

      .status-panel.status-error {
        background: var(--error-bg);
        border-color: var(--error-border);
        color: var(--error-text);
      }

      .status-icon {
        display: inline-flex;
        width: 18px;
        height: 18px;
        align-items: center;
        justify-content: center;
        flex: 0 0 18px;
        margin-top: 2px;
        border-radius: 999px;
        border: 2px solid currentColor;
        font-size: 0.72rem;
        line-height: 1;
      }

      .status-icon.loading {
        border-top-color: transparent;
        animation: spin 0.9s linear infinite;
      }

      .status-copy {
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 0;
      }

      .status-copy p {
        margin: 0;
        line-height: 1.65;
        font-size: 0.95rem;
        font-weight: 600;
        color: inherit;
      }

      .error-list {
        display: none;
        margin: 0;
        padding-left: 18px;
        font-size: 0.9rem;
        line-height: 1.65;
      }

      .error-list.visible {
        display: block;
      }

      .footnote {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.65;
        color: var(--muted);
      }

      .footer-note {
        margin: 0;
        font-size: 0.92rem;
        color: var(--muted);
      }

      @keyframes spin {
        from {
          transform: rotate(0deg);
        }
        to {
          transform: rotate(360deg);
        }
      }

      @media (min-width: 980px) {
        .main-card-inner {
          padding: 30px 32px;
        }

        .editor-layout {
          grid-template-columns: minmax(0, 1fr) 300px;
          align-items: stretch;
        }
      }

      @media (max-width: 720px) {
        main {
          padding: 28px 14px 52px;
        }

        .main-card-inner {
          padding: 18px;
        }

        .pane-header {
          align-items: flex-start;
          flex-direction: column;
        }

        textarea {
          min-height: 300px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <div class="page">
        <section class="hero">
          <h1>Paste YAML and get a PPTX instantly.</h1>
          <p>
            This demo validates weekly report YAML against the current schema and
            generates a PowerPoint deck right away.
          </p>
          <p class="subcopy">
            Use the sample input or paste your own report data. Submitted content
            is processed only to generate the file, and generated PPTX output is
            cleaned up after download by default.
          </p>
        </section>

        <section class="main-card">
          <div class="main-card-inner">
            <div class="editor-layout">
              <div class="editor-pane">
                <div class="pane-header">
                  <div class="pane-title">
                    <span class="pane-title-mark" aria-hidden="true"></span>
                    <span>YAML Input</span>
                  </div>
                  <button id="load-example" class="ghost-button" type="button">
                    Load Example
                  </button>
                </div>
                <textarea
                  id="report-yaml"
                  spellcheck="false"
                  aria-label="Report YAML input"
                  placeholder="Paste your YAML here..."
                ></textarea>
              </div>

              <aside class="status-pane">
                <div class="status-stack">
                  <section class="status-card">
                    <div class="status-label">Current Status</div>
                    <div id="status-panel" class="status-panel status-idle" aria-live="polite">
                      <span id="status-icon" class="status-icon" aria-hidden="true">i</span>
                      <div class="status-copy">
                        <p id="status-message">
                          Load the example or paste your own YAML, then generate a PPTX.
                        </p>
                        <ul id="error-list" class="error-list"></ul>
                      </div>
                    </div>
                  </section>

                  <button id="generate-button" class="primary-button" type="button">
                    <span id="generate-label">Generate PPTX</span>
                  </button>

                  <p class="footnote">
                    Current scope: built-in weekly template, pasted YAML input,
                    instant download
                  </p>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <p class="footer-note">
          Autoreport Public Demo - Submitted YAML is not retained, and generated
          PPTX files are cleaned up after download.
        </p>
      </div>
    </main>

    <script>
      const EXAMPLE_YAML = __EXAMPLE_YAML_JSON__;
      const textarea = document.getElementById("report-yaml");
      const loadExampleButton = document.getElementById("load-example");
      const generateButton = document.getElementById("generate-button");
      const statusPanel = document.getElementById("status-panel");
      const statusIcon = document.getElementById("status-icon");
      const statusMessageNode = document.getElementById("status-message");
      const errorList = document.getElementById("error-list");
      const generateLabel = document.getElementById("generate-label");

      function setStatus(mode, message, errors = []) {
        statusPanel.className = `status-panel status-${mode}`;
        statusMessageNode.textContent = message;
        errorList.innerHTML = "";
        errorList.classList.toggle("visible", errors.length > 0);

        if (mode === "loading") {
          statusIcon.textContent = "";
          statusIcon.className = "status-icon loading";
          generateLabel.textContent = "Generating...";
        } else if (mode === "success") {
          statusIcon.textContent = "OK";
          statusIcon.className = "status-icon";
          generateLabel.textContent = "Generate Again";
        } else if (mode === "error") {
          statusIcon.textContent = "!";
          statusIcon.className = "status-icon";
          generateLabel.textContent = "Generate PPTX";
        } else {
          statusIcon.textContent = "i";
          statusIcon.className = "status-icon";
          generateLabel.textContent = "Generate PPTX";
        }

        for (const item of errors) {
          const li = document.createElement("li");
          li.textContent = item;
          errorList.appendChild(li);
        }
      }

      function setBusy(isBusy, message) {
        generateButton.disabled = isBusy;
        if (isBusy) {
          setStatus("loading", message);
        }
      }

      loadExampleButton.addEventListener("click", () => {
        textarea.value = EXAMPLE_YAML;
        setStatus(
          "idle",
          "Sample YAML loaded. Review the content or generate the PPTX right away."
        );
      });

      generateButton.addEventListener("click", async () => {
        if (!textarea.value.trim()) {
          setStatus("error", "Generation failed. Please provide valid YAML input.");
          return;
        }

        setBusy(
          true,
          "Validating the YAML input and generating your PPTX file..."
        );

        try {
          const response = await fetch("/api/generate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              report_yaml: textarea.value,
            }),
          });

          if (!response.ok) {
            const payload = await response.json();
            generateButton.disabled = false;
            setStatus(
              "error",
              payload.message || "Generation failed. Review the error details and try again.",
              payload.errors || []
            );
            return;
          }

          const blob = await response.blob();
          const downloadUrl = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = downloadUrl;
          anchor.download = "weekly_report.pptx";
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(downloadUrl);

          generateButton.disabled = false;
          setStatus("success", "Generation complete. Your download should begin shortly.");
        } catch (error) {
          generateButton.disabled = false;
          setStatus(
            "error",
            "A network error occurred. Please wait a moment and try again."
          );
        }
      });
    </script>
  </body>
</html>""".replace("__EXAMPLE_YAML_JSON__", example_json)


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
    """Write structured request outcome logs without persisting YAML content."""

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
    """Build a consistent JSON error response."""

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
def generate_demo_report(payload: GenerateRequest) -> FileResponse | JSONResponse:
    """Generate a weekly report PPTX from pasted YAML text."""

    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        raw_data = parse_yaml_text(payload.report_yaml)
        temp_dir_path = Path(tempfile.mkdtemp(prefix="autoreport-web-"))
        output_path = temp_dir_path / "weekly_report.pptx"
        generated_path = generate_report_from_mapping(
            raw_data,
            output_path=output_path,
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
            message="Report validation failed.",
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
        filename="weekly_report.pptx",
        background=BackgroundTask(_cleanup_temp_dir, temp_dir_path),
    )
