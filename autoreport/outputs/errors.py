"""Output-layer exceptions shared by generation and writer code."""

from __future__ import annotations

from pathlib import Path


class TemplateNotFoundError(FileNotFoundError):
    """Raised when the requested presentation template does not exist."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        super().__init__(f"Template file not found: {template_path}")


class OutputWriteError(OSError):
    """Raised when the generated presentation cannot be written to disk."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        super().__init__(f"Could not write report file: {output_path}")


class TemplateLoadError(OSError):
    """Raised when a presentation template cannot be read as a `.pptx`."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        super().__init__(f"Invalid PowerPoint template file: {template_path}")


class TemplateReadError(OSError):
    """Raised when a presentation template cannot be read from disk."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        super().__init__(f"Could not read template file: {template_path}")


class TemplateCompatibilityError(ValueError):
    """Raised when a template lacks the layouts/placeholders Autoreport needs."""

    def __init__(self, template_path: Path | None, detail: str) -> None:
        self.template_path = template_path
        self.detail = detail
        target = str(template_path) if template_path is not None else "default template"
        super().__init__(
            "PowerPoint template is not compatible with the Autoreport contract: "
            f"{target} ({detail})"
        )
