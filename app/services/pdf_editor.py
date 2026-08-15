from datetime import date
from pathlib import Path

import pymupdf

from app.domain.models import (
    HighlightBox,
    PageEdits,
    StampKind,
    StampMark,
    Stroke,
    TextBox,
)


def hex_to_rgb(color: str) -> tuple[float, float, float]:
    value = color.removeprefix("#").strip()
    if len(value) != 6:
        raise ValueError(f"invalid color: {color}")
    r = int(value[0:2], 16) / 255
    g = int(value[2:4], 16) / 255
    b = int(value[4:6], 16) / 255
    return r, g, b


_STAMP_LABELS = {
    StampKind.APPROVED: "APPROVED",
    StampKind.PAID: "PAID",
    StampKind.DATE: None,
}


class PdfEditor:
    def apply_edits(self, pdf_path: Path, pages: list[PageEdits], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(pdf_path) as doc:
            for page_edits in pages:
                if page_edits.page_index < 0 or page_edits.page_index >= len(doc):
                    raise IndexError(f"page {page_edits.page_index} out of range")
                page = doc[page_edits.page_index]
                self._draw_highlights(page, page_edits.highlights)
                self._draw_strokes(page, page_edits.strokes)
                self._draw_texts(page, page_edits.texts)
                self._draw_stamps(page, page_edits.stamps)
            doc.save(out_path, garbage=4, deflate=True)
        return out_path

    def rotate_page(self, pdf_path: Path, page_index: int, degrees: int, out_path: Path) -> Path:
        if degrees not in (90, 180, 270, -90):
            raise ValueError("degrees must be 90, 180, 270, or -90")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(pdf_path) as doc:
            if page_index < 0 or page_index >= len(doc):
                raise IndexError(f"page {page_index} out of range")
            page = doc[page_index]
            page.set_rotation((page.rotation + degrees) % 360)
            doc.save(out_path, garbage=4, deflate=True)
        return out_path

    def _draw_strokes(self, page: pymupdf.Page, strokes: tuple[Stroke, ...]) -> None:
        if not strokes:
            return
        rect = page.rect
        shape = page.new_shape()
        for stroke in strokes:
            if len(stroke.points) < 2:
                continue
            points = [
                pymupdf.Point(p.x * rect.width, p.y * rect.height) for p in stroke.points
            ]
            shape.draw_polyline(points)
            width = max(0.5, stroke.width * rect.width)
            shape.finish(
                color=hex_to_rgb(stroke.color),
                width=width,
                closePath=False,
                stroke_opacity=1,
                fill=None,
            )
        shape.commit()

    def _draw_texts(self, page: pymupdf.Page, texts: tuple[TextBox, ...]) -> None:
        rect = page.rect
        for box in texts:
            if not box.text.strip():
                continue
            point = pymupdf.Point(box.x * rect.width, box.y * rect.height)
            fontsize = max(6, box.size * rect.height)
            page.insert_text(
                point,
                box.text,
                fontsize=fontsize,
                color=hex_to_rgb(box.color),
            )

    def _draw_highlights(self, page: pymupdf.Page, highlights: tuple[HighlightBox, ...]) -> None:
        if not highlights:
            return
        rect = page.rect
        shape = page.new_shape()
        for box in highlights:
            x0 = min(box.x0, box.x1) * rect.width
            y0 = min(box.y0, box.y1) * rect.height
            x1 = max(box.x0, box.x1) * rect.width
            y1 = max(box.y0, box.y1) * rect.height
            if abs(x1 - x0) < 1 or abs(y1 - y0) < 1:
                continue
            shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
            shape.finish(
                color=None,
                fill=hex_to_rgb(box.color),
                fill_opacity=0.35,
                width=0,
            )
        shape.commit()

    def _draw_stamps(self, page: pymupdf.Page, stamps: tuple[StampMark, ...]) -> None:
        rect = page.rect
        for stamp in stamps:
            label = _STAMP_LABELS[stamp.kind]
            if label is None:
                label = date.today().isoformat()
            fontsize = max(10, 0.035 * rect.height)
            text_width = pymupdf.get_text_length(label, fontsize=fontsize)
            pad_x = fontsize * 0.55
            pad_y = fontsize * 0.45
            cx = stamp.x * rect.width
            cy = stamp.y * rect.height
            box = pymupdf.Rect(
                cx - text_width / 2 - pad_x,
                cy - fontsize / 2 - pad_y,
                cx + text_width / 2 + pad_x,
                cy + fontsize / 2 + pad_y,
            )
            shape = page.new_shape()
            shape.draw_rect(box)
            shape.finish(color=(0.75, 0.12, 0.12), width=1.6, fill=None)
            shape.commit()
            page.insert_text(
                pymupdf.Point(box.x0 + pad_x, box.y1 - pad_y * 0.7),
                label,
                fontsize=fontsize,
                color=(0.75, 0.12, 0.12),
            )
