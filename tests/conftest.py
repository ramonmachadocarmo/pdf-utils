from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((72, 72), "hello pdf-utils")
    doc.set_metadata({"title": "Sample Title"})
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def multipage_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "multi.pdf"
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page(width=200, height=280)
        page.insert_text((40, 40), f"page {i + 1}")
    doc.save(path)
    doc.close()
    return path
