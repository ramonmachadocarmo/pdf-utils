from pathlib import Path

import pymupdf

from app.domain.models import PageInfo, PdfMeta, SearchHit


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

    def search(self, path: Path, query: str) -> list[SearchHit]:
        query = query.strip()
        if not query:
            return []
        hits: list[SearchHit] = []
        with pymupdf.open(path) as doc:
            for page_index, page in enumerate(doc):
                rect = page.rect
                for match in page.search_for(query):
                    hits.append(
                        SearchHit(
                            page_index=page_index,
                            text=page.get_textbox(match).strip() or query,
                            x0=match.x0 / rect.width,
                            y0=match.y0 / rect.height,
                            x1=match.x1 / rect.width,
                            y1=match.y1 / rect.height,
                        )
                    )
        return hits
