"""PowerPoint output writer placeholders.

This module will eventually translate rendered content into `.pptx` files using
an author-provided template.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class PowerPointWriter:
    """Placeholder writer for future PowerPoint export support."""

    def write(
        self,
        *,
        template_path: Path,
        output_path: Path,
        context: dict[str, Any],
    ) -> Path:
        """Write a PowerPoint file using a template and prepared context."""

        del template_path, output_path, context
        raise NotImplementedError("PowerPoint generation is not implemented yet.")

