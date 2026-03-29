"""Analyze local PresentationGo `.potx` references for branch-local design guidance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[4]
REFERENCE_LIBRARY_DIR = (
    REPO_ROOT.parent
    / "autoreport"
    / ".codex"
    / "template-library"
    / "2026-03-28"
    / "downloads"
    / "presentationgo"
)
VALIDATION_DIR = REPO_ROOT / "experiments" / "v04" / "validation"
VALIDATION_JSON_PATH = VALIDATION_DIR / "presentationgo-reference-analysis.json"
VALIDATION_REPORT_PATH = VALIDATION_DIR / "presentationgo-reference-analysis.md"
REFERENCE_FILES = (
    "datawave-insights-16x9.potx",
    "finance-business-16x9.potx",
    "modern-business-16x9.potx",
    "modern-navy-horizon-16x9.potx",
)
REFERENCE_NOTES = {
    "datawave-insights-16x9.potx": {
        "tone": "calm data-reporting",
        "why_it_matters": (
            "Strong fit for Autoreport editorial tonality because the palette is restrained "
            "and the closing layout already mixes picture and body zones."
        ),
        "reuse_bias": "palette + title rhythm",
    },
    "finance-business-16x9.potx": {
        "tone": "safe corporate baseline",
        "why_it_matters": (
            "Useful as a control because it stays close to stock Office structure."
        ),
        "reuse_bias": "baseline comparison only",
    },
    "modern-business-16x9.potx": {
        "tone": "broad layout library",
        "why_it_matters": (
            "Best source for structural ideas because it carries both `Content with "
            "Caption` and `Picture with Caption` plus multiple title/content variants."
        ),
        "reuse_bias": "mixed-layout patterns",
    },
    "modern-navy-horizon-16x9.potx": {
        "tone": "high-contrast editorial",
        "why_it_matters": (
            "Good source for stronger color blocking, but many layouts carry a "
            "decorative picture placeholder that could confuse template profiling."
        ),
        "reuse_bias": "accent system + edge decoration",
    },
}
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze local PresentationGo references used for v0.4 design work."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON payload.",
    )
    parser.add_argument(
        "--write-validation",
        action="store_true",
        help="Write the JSON and markdown artifacts into `experiments/v04/validation/`.",
    )
    return parser.parse_args()


def _load_xml(archive: ZipFile, part_name: str) -> ET.Element:
    return ET.fromstring(archive.read(part_name))


def _layout_summary(archive: ZipFile) -> list[dict[str, Any]]:
    layout_parts = sorted(
        name
        for name in archive.namelist()
        if name.startswith("ppt/slideLayouts/slideLayout")
        and name.endswith(".xml")
    )
    layouts: list[dict[str, Any]] = []
    for layout_part in layout_parts:
        root = _load_xml(archive, layout_part)
        c_sld = root.find("p:cSld", NS)
        placeholders: list[dict[str, Any]] = []
        for shape in root.findall("p:cSld/p:spTree/*", NS):
            placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
            if placeholder is None:
                placeholder = shape.find("p:nvPicPr/p:nvPr/p:ph", NS)
            if placeholder is None:
                continue
            placeholders.append(
                {
                    "idx": int(placeholder.get("idx")) if placeholder.get("idx") else None,
                    "type": placeholder.get("type") or "object?",
                }
            )
        layouts.append(
            {
                "part_name": layout_part,
                "name": c_sld.get("name") if c_sld is not None else Path(layout_part).name,
                "placeholders": placeholders,
            }
        )
    return layouts


def _theme_summary(archive: ZipFile) -> dict[str, Any]:
    theme_path = next(
        (
            name
            for name in archive.namelist()
            if name.startswith("ppt/theme/theme")
            and name.endswith(".xml")
        ),
        None,
    )
    if theme_path is None:
        return {"colors": [], "fonts": {}}

    root = _load_xml(archive, theme_path)
    color_scheme = root.find(".//a:clrScheme", NS)
    font_scheme = root.find(".//a:fontScheme", NS)

    colors: list[dict[str, str]] = []
    if color_scheme is not None:
        for child in list(color_scheme):
            swatch = list(child)[0] if list(child) else None
            colors.append(
                {
                    "name": child.tag.split("}")[-1],
                    "value": (
                        swatch.get("lastClr")
                        or swatch.get("val")
                        or ""
                    )
                    if swatch is not None
                    else "",
                }
            )

    fonts = {}
    if font_scheme is not None:
        major_latin = font_scheme.find("a:majorFont/a:latin", NS)
        minor_latin = font_scheme.find("a:minorFont/a:latin", NS)
        fonts = {
            "major_latin": major_latin.get("typeface") if major_latin is not None else "",
            "minor_latin": minor_latin.get("typeface") if minor_latin is not None else "",
        }

    return {"colors": colors, "fonts": fonts}


def analyze_reference(path: Path) -> dict[str, Any]:
    with ZipFile(path, "r") as archive:
        presentation_root = _load_xml(archive, "ppt/presentation.xml")
        slide_size = presentation_root.find("p:sldSz", NS)
        layouts = _layout_summary(archive)
        theme = _theme_summary(archive)
        media_assets = len(
            [
                name
                for name in archive.namelist()
                if name.startswith("ppt/media/")
            ]
        )

    layout_names = [layout["name"] for layout in layouts]
    has_picture_with_caption = any(
        layout["name"] == "Picture with Caption"
        or (
            any(ph["type"] == "pic" for ph in layout["placeholders"])
            and any(ph["type"] == "body" for ph in layout["placeholders"])
        )
        for layout in layouts
    )
    decorative_picture_layouts = sum(
        1
        for layout in layouts
        if any(ph["type"] == "pic" for ph in layout["placeholders"])
    )

    return {
        "file_name": path.name,
        "source_exists": path.exists(),
        "source_library_snapshot": "template-library/2026-03-28/presentationgo",
        "slide_size": {
            "cx": int(slide_size.get("cx")) if slide_size is not None else None,
            "cy": int(slide_size.get("cy")) if slide_size is not None else None,
        },
        "layout_count": len(layouts),
        "layout_names": layout_names,
        "layouts": layouts,
        "theme": theme,
        "media_assets": media_assets,
        "signals": {
            "has_picture_with_caption": has_picture_with_caption,
            "decorative_picture_layouts": decorative_picture_layouts,
        },
        **REFERENCE_NOTES[path.name],
    }


def collect_analysis() -> dict[str, Any]:
    references = [
        analyze_reference(REFERENCE_LIBRARY_DIR / file_name)
        for file_name in REFERENCE_FILES
    ]
    recommended = {
        "structure_reference": "modern-business-16x9.potx",
        "palette_reference": "datawave-insights-16x9.potx",
        "accent_reference": "modern-navy-horizon-16x9.potx",
        "baseline_control": "finance-business-16x9.potx",
    }
    translation = {
        "keep": [
            "16:9 aspect ratio",
            "editorial title hierarchy",
            "calm navy + teal + coral palette",
            "decorative energy pushed to edges instead of behind the main text block",
        ],
        "avoid": [
            "layout-wide decorative picture placeholders on text-first slides",
            "dense multi-placeholder bodies before the runtime profiler boundary is patched",
            "theme defaults that collapse back to plain stock Office styling",
        ],
    }
    return {
        "source_library_dir": "template-library/2026-03-28/presentationgo",
        "references": references,
        "recommended_translation": recommended,
        "v04_template_translation_rules": translation,
    }


def render_markdown_report(analysis: dict[str, Any]) -> str:
    references = analysis["references"]
    summary_lines = []
    for reference in references:
        colors = ", ".join(
            f"{color['name']}={color['value']}"
            for color in reference["theme"]["colors"][:6]
        )
        summary_lines.append(
            "\n".join(
                [
                    f"- `{reference['file_name']}`",
                    f"  tone: `{reference['tone']}`",
                    f"  layouts: `{reference['layout_count']}`",
                    f"  reuse bias: `{reference['reuse_bias']}`",
                    f"  key theme colors: `{colors}`",
                    f"  why it matters: {reference['why_it_matters']}",
                ]
            )
        )

    translation = analysis["v04_template_translation_rules"]
    recommended = analysis["recommended_translation"]
    return f"""# PresentationGo Reference Analysis

## Summary

- Source snapshot: `template-library/2026-03-28/presentationgo`
- Structure reference: `{recommended['structure_reference']}`
- Palette reference: `{recommended['palette_reference']}`
- Accent reference: `{recommended['accent_reference']}`
- Baseline control: `{recommended['baseline_control']}`

## Reference Notes

{chr(10).join(summary_lines)}

## Translation Rules

### Keep

{chr(10).join(f"- {item}" for item in translation['keep'])}

### Avoid

{chr(10).join(f"- {item}" for item in translation['avoid'])}
"""


def write_validation_artifacts(analysis: dict[str, Any]) -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON_PATH.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    VALIDATION_REPORT_PATH.write_text(
        render_markdown_report(analysis),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    analysis = collect_analysis()
    if args.write_validation:
        write_validation_artifacts(analysis)
    print(json.dumps(analysis, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
