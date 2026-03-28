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
_FULL_EXAMPLE_PAYLOAD = scaffold_payload(_BUILT_IN_CONTRACT)
_TEXT_ONLY_EXAMPLE_PAYLOAD = scaffold_payload(_BUILT_IN_CONTRACT)
_TEXT_ONLY_EXAMPLE_PAYLOAD.slides = [
    slide for slide in _TEXT_ONLY_EXAMPLE_PAYLOAD.slides if slide.kind != "text_image"
]
DEFAULT_PAYLOAD_YAML = serialize_document(
    _TEXT_ONLY_EXAMPLE_PAYLOAD.to_dict(),
    fmt="yaml",
).strip()
FULL_EXAMPLE_PAYLOAD_YAML = serialize_document(
    _FULL_EXAMPLE_PAYLOAD.to_dict(),
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
    image_payload_json = json.dumps(FULL_EXAMPLE_PAYLOAD_YAML)
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
      .panel-copy {
        margin: 0 0 12px;
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.6;
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
        list-style: none;
        margin: 12px 0 0;
        padding: 0;
        color: var(--muted);
        line-height: 1.6;
        display: grid;
        gap: 10px;
      }
      .upload-item {
        border: 1px solid var(--border);
        border-radius: 16px;
        background: #fff;
        padding: 12px;
      }
      .upload-meta {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
      }
      .upload-ref {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 74px;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font: 0.82rem/1.2 "Cascadia Mono", Consolas, monospace;
        font-weight: 700;
      }
      .upload-name {
        color: var(--text);
        font-size: 0.92rem;
      }
      .mini-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }
      .mini-actions button {
        padding: 8px 12px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
      }
      .upload-snippet {
        margin-top: 10px;
        border-radius: 12px;
        background: var(--panel);
        padding: 10px 12px;
        color: var(--muted);
        font: 0.85rem/1.5 "Cascadia Mono", Consolas, monospace;
        white-space: pre-wrap;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 14px;
      }
      .helper-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-top: 16px;
      }
      .helper-card {
        border: 1px solid var(--border);
        border-radius: 16px;
        background: var(--panel);
        padding: 14px;
      }
      .helper-card h3 {
        margin: 0 0 8px;
        font-size: 0.95rem;
      }
      .helper-card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.5;
      }
      .quick-actions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px;
        margin-top: 16px;
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
      .summary-list {
        margin: 0;
        padding-left: 18px;
        color: var(--muted);
        line-height: 1.6;
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
      .status-hints {
        margin: 10px 0 0;
        padding-left: 18px;
        color: var(--accent);
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
            <p class="panel-copy">
              This is the template's capability map. It tells you which slide patterns
              exist and which slots each pattern accepts.
            </p>
            <textarea id="template-contract" readonly aria-label="Template contract"></textarea>
          </div>
          <div class="panel">
            <h2>Report Payload</h2>
            <p class="panel-copy">
              This is the content you want the deck to say. Edit the title slide, add
              slides, and point any text-image slide at an uploaded image ref.
            </p>
            <textarea id="payload-yaml" aria-label="Report payload"></textarea>
            <div class="actions">
              <button id="load-example" class="ghost" type="button">Load Example</button>
              <button id="load-image-example" class="ghost" type="button">Load Image Example</button>
            </div>
            <div class="quick-actions">
              <button id="insert-text-slide" class="ghost" type="button">Insert Text Slide</button>
              <button id="insert-metrics-slide" class="ghost" type="button">Insert Metrics Slide</button>
              <button id="insert-text-image-slide" class="ghost" type="button">Insert Text + Image Slide</button>
            </div>
          </div>
        </div>
        <div class="controls">
          <div class="upload-box">
            <h2>Image Uploads</h2>
            <p class="hero-copy" style="text-align:left; margin:0 0 10px; max-width:none;">
              Upload images, then use the helper buttons to insert a ref or a full
              text-image slide without hunting through the YAML by hand.
            </p>
            <div class="helper-grid">
              <div class="helper-card">
                <h3>Template Contract</h3>
                <p>Read this first when another AI needs to know what the template can accept.</p>
              </div>
              <div class="helper-card">
                <h3>Report Payload</h3>
                <p>Use slide blocks to describe what each slide should say, not how to draw it.</p>
              </div>
              <div class="helper-card">
                <h3>Image Uploads</h3>
                <p>Each upload gets an <code>image_1</code>-style ref. Use that ref in a text-image slide.</p>
              </div>
            </div>
            <input id="image-files" type="file" multiple accept=".png,.jpg,.jpeg">
            <ul id="upload-list" class="upload-list"></ul>
          </div>
          <div class="status-box">
            <h3>Current Status</h3>
            <div id="status-message" class="status-message">
              The built-in editorial contract is loaded. Review the payload, check the deck summary, or upload images and generate the deck.
            </div>
            <ul id="status-errors" class="status-errors"></ul>
            <ul id="status-hints" class="status-hints"></ul>
            <div class="actions" style="margin-top:16px;">
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
            <h3 style="margin-top:18px;">Current Deck Summary</h3>
            <ul id="deck-summary" class="summary-list"></ul>
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
      const IMAGE_EXAMPLE_PAYLOAD = __IMAGE_PAYLOAD_JSON__;
      const contractNode = document.getElementById("template-contract");
      const payloadNode = document.getElementById("payload-yaml");
      const fileInput = document.getElementById("image-files");
      const uploadList = document.getElementById("upload-list");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const statusHints = document.getElementById("status-hints");
      const deckSummary = document.getElementById("deck-summary");
      const loadExampleButton = document.getElementById("load-example");
      const loadImageExampleButton = document.getElementById("load-image-example");
      const generateButton = document.getElementById("generate-button");
      const insertTextSlideButton = document.getElementById("insert-text-slide");
      const insertMetricsSlideButton = document.getElementById("insert-metrics-slide");
      const insertTextImageSlideButton = document.getElementById("insert-text-image-slide");

      let uploadedRefs = [];

      function normalizeYamlScalar(rawValue) {
        const value = String(rawValue || "").trim();
        if (!value) {
          return "";
        }
        const quoted = value.match(/^['"](.*)['"]$/);
        return quoted ? quoted[1] : value;
      }

      function getPreferredImageRef() {
        return uploadedRefs.length ? uploadedRefs[uploadedRefs.length - 1].ref : "image_1";
      }

      function insertTextAtCursor(text) {
        const start = typeof payloadNode.selectionStart === "number"
          ? payloadNode.selectionStart
          : payloadNode.value.length;
        const end = typeof payloadNode.selectionEnd === "number"
          ? payloadNode.selectionEnd
          : payloadNode.value.length;
        payloadNode.focus();
        payloadNode.setRangeText(text, start, end, "end");
        updateDeckSummary();
      }

      function appendSummaryItem(text) {
        const li = document.createElement("li");
        li.textContent = text;
        deckSummary.appendChild(li);
      }

      function parsePayloadOutline(text) {
        const outline = {
          title: "",
          contentsEnabled: true,
          slides: [],
          warnings: [],
        };
        const lines = text.split("\\n");
        let section = "";
        let currentSlide = null;
        let inImageBlock = false;

        for (const rawLine of lines) {
          const trimmed = rawLine.trim();
          if (!trimmed || trimmed.startsWith("#")) {
            continue;
          }

          if (!rawLine.startsWith(" ")) {
            section = "";
            currentSlide = null;
            inImageBlock = false;
            continue;
          }

          if (trimmed === "title_slide:") {
            section = "title_slide";
            currentSlide = null;
            inImageBlock = false;
            continue;
          }
          if (trimmed === "contents:") {
            section = "contents";
            currentSlide = null;
            inImageBlock = false;
            continue;
          }
          if (trimmed === "slides:") {
            section = "slides";
            currentSlide = null;
            inImageBlock = false;
            continue;
          }

          if (section === "title_slide" && trimmed.startsWith("title:")) {
            outline.title = normalizeYamlScalar(trimmed.slice("title:".length));
            continue;
          }

          if (section === "contents" && trimmed.startsWith("enabled:")) {
            outline.contentsEnabled = normalizeYamlScalar(
              trimmed.slice("enabled:".length)
            ).toLowerCase() !== "false";
            continue;
          }

          if (section !== "slides") {
            continue;
          }

          if (trimmed.startsWith("- kind:")) {
            currentSlide = {
              kind: normalizeYamlScalar(trimmed.slice("- kind:".length)),
              title: "Untitled slide",
              imageRefs: [],
            };
            outline.slides.push(currentSlide);
            inImageBlock = false;
            continue;
          }

          if (!currentSlide) {
            continue;
          }

          if (trimmed.startsWith("title:")) {
            currentSlide.title = normalizeYamlScalar(trimmed.slice("title:".length));
            continue;
          }

          if (trimmed === "image:") {
            inImageBlock = true;
            continue;
          }

          if (trimmed.startsWith("caption:") || trimmed.startsWith("slot_overrides:")) {
            inImageBlock = false;
          }

          if (inImageBlock && trimmed.startsWith("ref:")) {
            currentSlide.imageRefs.push(
              normalizeYamlScalar(trimmed.slice("ref:".length))
            );
          }
        }

        if (!outline.title) {
          outline.warnings.push("Cover title is missing or unreadable.");
        }
        if (!outline.slides.length) {
          outline.warnings.push("No body slide blocks are currently detectable.");
        }
        return outline;
      }

      function extractFieldPath(errorText) {
        const match = /Field '([^']+)'/.exec(errorText || "");
        return match ? match[1] : "";
      }

      function describeFieldSection(fieldPath) {
        if (!fieldPath) {
          return "Payload";
        }
        if (fieldPath === "payload_yaml") {
          return "Payload Root";
        }
        if (fieldPath.startsWith("title_slide.")) {
          return "Title Slide";
        }
        if (fieldPath.startsWith("contents.")) {
          return "Contents";
        }
        if (fieldPath.startsWith("image_manifest[")) {
          return "Uploaded Images";
        }
        const slideMatch = fieldPath.match(/^slides\\[(\\d+)\\]/);
        if (slideMatch) {
          return `Slide ${Number(slideMatch[1]) + 1}`;
        }
        return "Payload";
      }

      function buildAuthoringFeedback(payload) {
        const errors = Array.isArray(payload.errors) ? payload.errors : [];

        if (payload.error_type === "yaml_parse_error") {
          const lineMatch = /line (\\d+)/i.exec(payload.message || "");
          const columnMatch = /column (\\d+)/i.exec(payload.message || "");
          const location = lineMatch
            ? ` near line ${lineMatch[1]}${columnMatch ? `, column ${columnMatch[1]}` : ""}`
            : "";
          return {
            message: `YAML parsing failed${location}. Check indentation, colons, and list spacing before generating again.`,
            hints: [
              "If the payload shape drifted, restore a starter example and reapply only the content you need.",
            ],
          };
        }

        if (payload.error_type === "validation_error" && errors.length) {
          const fieldPaths = errors.map(extractFieldPath).filter(Boolean);
          const sections = [];
          for (const fieldPath of fieldPaths) {
            const label = describeFieldSection(fieldPath);
            if (!sections.includes(label)) {
              sections.push(label);
            }
          }
          const hints = [];
          if (fieldPaths.length) {
            hints.push(`Start with ${fieldPaths[0]}.`);
          }
          if (fieldPaths.some((fieldPath) => fieldPath.startsWith("title_slide."))) {
            hints.push("Title Slide issues block the whole deck, so fix those first.");
          }
          if (fieldPaths.some((fieldPath) => fieldPath.includes(".image.ref"))) {
            hints.push("Use Image Uploads -> Insert Ref or Add Slide so the payload reuses a real uploaded image ref.");
          }
          return {
            message: sections.length
              ? `Validation stopped in ${sections.join(", ")}. Fix the field list below and try Generate PPTX again.`
              : "Payload validation failed. Fix the field list below and try Generate PPTX again.",
            hints,
          };
        }

        return {
          message: payload.message || "Generation failed.",
          hints: [],
        };
      }

      function renderUploads() {
        uploadList.innerHTML = "";
        if (!uploadedRefs.length) {
          const li = document.createElement("li");
          li.className = "upload-item";
          li.textContent = "No uploaded files yet.";
          uploadList.appendChild(li);
          return;
        }
        for (const item of uploadedRefs) {
          const li = document.createElement("li");
          li.className = "upload-item";

          const meta = document.createElement("div");
          meta.className = "upload-meta";

          const ref = document.createElement("span");
          ref.className = "upload-ref";
          ref.textContent = item.ref;

          const name = document.createElement("span");
          name.className = "upload-name";
          name.textContent = item.file.name;

          const actions = document.createElement("div");
          actions.className = "mini-actions";

          const insertRefButton = document.createElement("button");
          insertRefButton.type = "button";
          insertRefButton.textContent = "Insert Ref";
          insertRefButton.addEventListener("click", () => {
            insertTextAtCursor(item.ref);
            setStatus(
              `${item.ref} was inserted at the current payload cursor.`,
              [],
              ["Use it under slides[*].image.ref or inside an image slot override."]
            );
          });

          const addSlideButton = document.createElement("button");
          addSlideButton.type = "button";
          addSlideButton.textContent = "Add Slide";
          addSlideButton.addEventListener("click", () => {
            const appended = appendSlideBlock(buildTextImageSlideBlock(item.ref));
            if (appended) {
              setStatus(
                `A text-image slide block using ${item.ref} was appended to the payload.`,
                [],
                ["Replace the draft copy, keep the ref in place, and generate again when ready."]
              );
            }
          });

          const snippet = document.createElement("div");
          snippet.className = "upload-snippet";
          snippet.textContent = `image:\\n  ref: ${item.ref}\\n  fit: contain`;

          meta.append(ref, name);
          actions.append(insertRefButton, addSlideButton);
          li.append(meta, actions, snippet);
          uploadList.appendChild(li);
        }
      }

      function updateDeckSummary() {
        deckSummary.innerHTML = "";
        const outline = parsePayloadOutline(payloadNode.value);
        const imageUsage = new Map();
        for (const slide of outline.slides) {
          for (const ref of slide.imageRefs) {
            imageUsage.set(ref, (imageUsage.get(ref) || 0) + 1);
          }
        }
        const expectedSlideCount = 1 + outline.slides.length + (outline.contentsEnabled ? 1 : 0);
        const uploadedRefNames = uploadedRefs.map((item) => item.ref);
        const usedImageRefs = Array.from(imageUsage.entries())
          .map(([ref, count]) => `${ref} (${count} slide${count === 1 ? "" : "s"})`)
          .join(", ");
        const missingUploads = Array.from(imageUsage.keys()).filter(
          (ref) => uploadedRefNames.length && !uploadedRefNames.includes(ref)
        );
        const unusedUploads = uploadedRefNames.filter((ref) => !imageUsage.has(ref));

        appendSummaryItem(`Expected generated slides: ${expectedSlideCount}`);
        appendSummaryItem(`Cover title: ${outline.title || "missing"}`);
        appendSummaryItem(
          `Slide titles: ${outline.slides.length ? outline.slides.map((slide, index) => `${index + 1}. ${slide.title}`).join(" | ") : "none yet"}`
        );
        appendSummaryItem(
          `Slide kinds: ${outline.slides.length ? outline.slides.map((slide) => slide.kind || "unknown").join(", ") : "none yet"}`
        );
        appendSummaryItem(`Image refs in payload: ${usedImageRefs || "none"}`);
        appendSummaryItem(`Uploaded image refs ready: ${uploadedRefNames.length ? uploadedRefNames.join(", ") : "none"}`);
        appendSummaryItem(`Unused uploaded refs: ${unusedUploads.length ? unusedUploads.join(", ") : "none"}`);
        if (missingUploads.length) {
          appendSummaryItem(`Payload refs still missing uploads: ${missingUploads.join(", ")}`);
        }
        for (const warning of outline.warnings) {
          appendSummaryItem(`Summary note: ${warning}`);
        }
      }

      function appendSlideBlock(block) {
        const trimmed = payloadNode.value.trimEnd();
        if (!trimmed.includes("  slides:")) {
          setStatus(
            "Payload must contain report_payload.slides before helper blocks can be inserted.",
            [],
            ["Restore a starter payload or add a slides: list first."]
          );
          return false;
        }
        payloadNode.value = `${trimmed}\\n${block}\\n`;
        updateDeckSummary();
        return true;
      }

      function buildTextSlideBlock() {
        return [
          "    - kind: text",
          "      title: New Text Slide",
          "      include_in_contents: true",
          "      body:",
          "        - Add the key message for this slide.",
          "        - Add a supporting detail or second bullet.",
          "      slot_overrides: {}",
        ].join("\\n");
      }

      function buildMetricsSlideBlock() {
        return [
          "    - kind: metrics",
          "      title: New Metrics Slide",
          "      include_in_contents: true",
          "      items:",
          "        - label: Metric label",
          "          value: 10",
          "        - label: Second metric",
          "          value: 24",
          "      slot_overrides: {}",
        ].join("\\n");
      }

      function buildTextImageSlideBlock(preferredRef = getPreferredImageRef()) {
        return [
          "    - kind: text_image",
          "      title: New Text + Image Slide",
          "      include_in_contents: true",
          "      body:",
          "        - Add the message that should sit beside the image.",
          "        - Add one supporting proof point.",
          "      image:",
          `        ref: ${preferredRef}`,
          "        fit: contain",
          `      caption: ${preferredRef} visual`,
          "      slot_overrides: {}",
        ].join("\\n");
      }

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

      contractNode.value = CONTRACT_YAML;
      payloadNode.value = EXAMPLE_PAYLOAD;
      renderUploads();
      updateDeckSummary();

      loadExampleButton.addEventListener("click", () => {
        payloadNode.value = EXAMPLE_PAYLOAD;
        setStatus(
          "Starter payload restored. You can edit it directly or upload images for image refs.",
          [],
          ["The deck summary now tracks expected slide count, slide titles, and image-ref usage as you edit."]
        );
        updateDeckSummary();
      });

      loadImageExampleButton.addEventListener("click", () => {
        payloadNode.value = IMAGE_EXAMPLE_PAYLOAD;
        setStatus(
          "Image-capable starter payload restored. Upload an image or keep the default image_1 ref.",
          [],
          ["Use Insert Ref or Add Slide from Image Uploads when you want to replace the placeholder ref quickly."]
        );
        updateDeckSummary();
      });

      payloadNode.addEventListener("input", () => {
        updateDeckSummary();
      });

      fileInput.addEventListener("change", () => {
        uploadedRefs = Array.from(fileInput.files || []).map((file, index) => ({
          ref: `image_${index + 1}`,
          file,
        }));
        renderUploads();
        if (uploadedRefs.length) {
          setStatus(
            "Uploads are ready. Use Insert Ref or Add Slide to place them without manual copy/paste hunting.",
            [],
            [`Ready refs: ${uploadedRefs.map((item) => item.ref).join(", ")}`]
          );
        } else {
          setStatus("No uploads selected.");
        }
        updateDeckSummary();
      });

      insertTextSlideButton.addEventListener("click", () => {
        const appended = appendSlideBlock(buildTextSlideBlock());
        if (appended) {
          setStatus("A text slide block was appended to the payload.");
        }
      });

      insertMetricsSlideButton.addEventListener("click", () => {
        const appended = appendSlideBlock(buildMetricsSlideBlock());
        if (appended) {
          setStatus("A metrics slide block was appended to the payload.");
        }
      });

      insertTextImageSlideButton.addEventListener("click", () => {
        const appended = appendSlideBlock(buildTextImageSlideBlock());
        if (appended) {
          setStatus(
            "A text-image slide block was appended to the payload.",
            [],
            [uploadedRefs.length ? `The latest uploaded ref (${getPreferredImageRef()}) was prefilled for you.` : "Upload an image when you want to replace the default image_1 placeholder."]
          );
        }
      });

      generateButton.addEventListener("click", async () => {
        const payloadYaml = payloadNode.value.trim();
        if (!payloadYaml) {
          setStatus(
            "Generation failed. Please provide payload YAML.",
            [],
            ["Load a starter example if you want a contract-aligned payload scaffold."]
          );
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
            const feedback = buildAuthoringFeedback(payload);
            generateButton.disabled = false;
            setStatus(
              feedback.message,
              payload.errors || [],
              feedback.hints
            );
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
</html>""".replace("__CONTRACT_JSON__", contract_json).replace("__PAYLOAD_JSON__", payload_json).replace("__IMAGE_PAYLOAD_JSON__", image_payload_json)


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

        try:
            image_manifest = json.loads(image_manifest_raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                [
                    "Field 'image_manifest' must be a valid JSON list."
                ]
            ) from exc
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
