"""PowerPoint output support for contract-first Autoreport decks."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.exc import PackageNotFoundError
from pptx.parts.image import Image
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.util import Pt

from autoreport.outputs.errors import (
    OutputWriteError,
    TemplateLoadError,
    TemplateNotFoundError,
    TemplateReadError,
)
from autoreport.templates.autofill import (
    FillPlan,
    PlannedImageFill,
    PlannedSlide,
    PlannedTextFill,
    SlideDecoration,
)


class PowerPointWriter:
    """Write report content into a `.pptx` presentation."""

    def write_fill_plan(
        self,
        *,
        presentation: Presentation,
        output_path: Path,
        fill_plan: FillPlan,
    ) -> Path:
        """Write a presentation from a template-aware slide plan."""

        self._clear_slides(presentation)
        for planned_slide in fill_plan.slides:
            self._write_planned_slide(presentation, planned_slide)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            presentation.save(str(output_path))
        except OSError as exc:
            raise OutputWriteError(output_path) from exc

        return output_path

    def _load_presentation(self, template_path: Path | None) -> Presentation:
        """Load an existing template or fall back to the default presentation."""

        if template_path is None:
            return Presentation()

        if not template_path.exists() or not template_path.is_file():
            raise TemplateNotFoundError(template_path)

        try:
            return Presentation(str(template_path))
        except (BadZipFile, KeyError, PackageNotFoundError, ValueError) as exc:
            raise TemplateLoadError(template_path) from exc
        except OSError as exc:
            raise TemplateReadError(template_path) from exc

    def _clear_slides(self, presentation: Presentation) -> None:
        """Remove existing slides while preserving the template theme."""

        slide_id_list = list(presentation.slides._sldIdLst)
        for slide_id in slide_id_list:
            relationship_id = slide_id.rId
            presentation.part.drop_rel(relationship_id)
            presentation.slides._sldIdLst.remove(slide_id)

    def _write_planned_slide(
        self,
        presentation: Presentation,
        planned_slide: PlannedSlide,
    ) -> None:
        """Render one planned slide into the target presentation."""

        slide = presentation.slides.add_slide(
            presentation.slide_layouts[planned_slide.layout_index]
        )
        for decoration in planned_slide.decorations:
            self._add_decoration_shape(slide, decoration)
        for image_fill in planned_slide.image_fills:
            self._write_image_fill(slide, image_fill)
        for text_fill in planned_slide.text_fills:
            self._write_text_fill(slide, text_fill)

    def _write_text_fill(self, slide, fill: PlannedTextFill) -> None:
        shape = self._resolve_text_shape(slide, fill.slot)
        if fill.text is not None:
            self._write_text_block(shape, fill.text, fill.font_size)
            return
        self._write_text_items(shape, fill.items, fill.font_size)

    def _write_image_fill(self, slide, fill: PlannedImageFill) -> None:
        if fill.slot.placeholder_index is not None and fill.fit == "cover":
            placeholder = slide.placeholders[fill.slot.placeholder_index]
            picture = placeholder.insert_picture(str(fill.image_path))
            return

        self._add_picture_to_bounds(
            slide,
            image_path=fill.image_path,
            left=fill.slot.x,
            top=fill.slot.y,
            width=fill.slot.width,
            height=fill.slot.height,
            fit=fill.fit,
        )

    def _add_picture_to_bounds(
        self,
        slide,
        *,
        image_path: Path,
        left: int,
        top: int,
        width: int,
        height: int,
        fit: str,
    ) -> None:
        image = Image.from_file(str(image_path))
        image_width, image_height = image.size
        image_ratio = image_width / image_height
        slot_ratio = width / height

        if fit == "contain":
            scale = min(width / image_width, height / image_height)
            scaled_width = int(image_width * scale)
            scaled_height = int(image_height * scale)
            offset_left = left + max(0, (width - scaled_width) // 2)
            offset_top = top + max(0, (height - scaled_height) // 2)
            slide.shapes.add_picture(
                str(image_path),
                offset_left,
                offset_top,
                width=scaled_width,
                height=scaled_height,
            )
            return

        picture = slide.shapes.add_picture(
            str(image_path),
            left,
            top,
            width=width,
            height=height,
        )
        if image_ratio > slot_ratio:
            crop = (1 - (slot_ratio / image_ratio)) / 2
            picture.crop_left = crop
            picture.crop_right = crop
            return
        crop = (1 - (image_ratio / slot_ratio)) / 2
        picture.crop_top = crop
        picture.crop_bottom = crop

    def _resolve_text_shape(self, slide, slot):
        if slot.placeholder_index is not None:
            return slide.placeholders[slot.placeholder_index]
        return slide.shapes.add_textbox(
            slot.x,
            slot.y,
            slot.width,
            slot.height,
        )

    def _write_text_block(
        self,
        shape,
        text: str,
        font_size: int | None,
    ) -> None:
        shape.text = text
        if font_size is not None:
            self._apply_font_size(shape.text_frame, font_size)

    def _write_text_items(
        self,
        shape,
        items: list[str],
        font_size: int | None,
    ) -> None:
        text_frame = shape.text_frame
        text_frame.clear()
        for index, item in enumerate(items):
            paragraph = (
                text_frame.paragraphs[0]
                if index == 0
                else text_frame.add_paragraph()
            )
            paragraph.text = item
            if font_size is not None:
                paragraph.font.size = Pt(font_size)

    def _add_decoration_shape(self, slide, decoration: SlideDecoration) -> None:
        auto_shape_type = {
            "rectangle": MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            "rounded_rectangle": MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        }[decoration.shape_type]
        shape = slide.shapes.add_shape(
            auto_shape_type,
            decoration.x,
            decoration.y,
            decoration.width,
            decoration.height,
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(*decoration.fill_rgb)
        if decoration.line_rgb is None:
            shape.line.fill.background()
        else:
            shape.line.color.rgb = RGBColor(*decoration.line_rgb)

    def _apply_font_size(self, text_frame, font_size: int) -> None:
        for paragraph in text_frame.paragraphs:
            paragraph.font.size = Pt(font_size)
