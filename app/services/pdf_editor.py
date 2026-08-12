from pathlib import Path

import pymupdf

from app.domain.models import PageStrokes, Stroke


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    value = color.removeprefix("#").strip()
    if len(value) != 6:
        raise ValueError(f"cor inválida: {color}")
    r = int(value[0:2], 16) / 255
    g = int(value[2:4], 16) / 255
    b = int(value[4:6], 16) / 255
    return r, g, b


class PdfEditor:
    def apply_ink(self, pdf_path: Path, pages: list[PageStrokes], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(pdf_path) as doc:
            for page_strokes in pages:
                if page_strokes.page_index < 0 or page_strokes.page_index >= len(doc):
                    raise IndexError(f"page {page_strokes.page_index} out of range")
                page = doc[page_strokes.page_index]
                self._draw_page(page, page_strokes.strokes)
            doc.save(out_path, garbage=4, deflate=True)
        return out_path

    def _draw_page(self, page: pymupdf.Page, strokes: tuple[Stroke, ...]) -> None:
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
                color=_hex_to_rgb(stroke.color),
                width=width,
                closePath=False,
                stroke_opacity=1,
                fill=None,
            )
        shape.commit()
