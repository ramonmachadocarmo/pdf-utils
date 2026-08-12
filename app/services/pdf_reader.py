from pathlib import Path

import pymupdf

from app.domain.models import PageInfo, PdfMeta


class PdfReader:
    def read_meta(self, path: Path) -> PdfMeta:
        with pymupdf.open(path) as doc:
            pages = tuple(
                PageInfo(index=i, width=page.rect.width, height=page.rect.height)
                for i, page in enumerate(doc)
            )
            title = (doc.metadata or {}).get("title") or path.stem
            return PdfMeta(page_count=len(doc), title=title, pages=pages)

    def render_page(self, path: Path, page_index: int, dpi: int = 120) -> bytes:
        with pymupdf.open(path) as doc:
            if page_index < 0 or page_index >= len(doc):
                raise IndexError(f"page {page_index} out of range")
            page = doc[page_index]
            matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            return pix.tobytes("png")
