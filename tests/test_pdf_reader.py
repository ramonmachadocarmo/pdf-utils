from pathlib import Path

import pytest

from app.services.pdf_reader import PdfReader


def test_read_meta(sample_pdf: Path):
    meta = PdfReader().read_meta(sample_pdf)
    assert meta.page_count == 1
    assert meta.title == "Sample Title"
    assert meta.pages[0].width == 300
    assert meta.pages[0].height == 400


def test_read_meta_falls_back_to_stem(tmp_path: Path):
    import pymupdf

    path = tmp_path / "fallback-name.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()

    meta = PdfReader().read_meta(path)
    assert meta.title == "fallback-name"


def test_render_page_returns_png(sample_pdf: Path):
    png = PdfReader().render_page(sample_pdf, 0, dpi=72)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_page_out_of_range(sample_pdf: Path):
    with pytest.raises(IndexError):
        PdfReader().render_page(sample_pdf, 99)


def test_search_finds_text(sample_pdf: Path):
    hits = PdfReader().search(sample_pdf, "hello")
    assert len(hits) >= 1
    assert hits[0].page_index == 0
    assert hits[0].text.lower().startswith("hello")
    assert hits[0].x1 > hits[0].x0


def test_search_returns_matched_text_not_query(tmp_path: Path):
    import pymupdf

    path = tmp_path / "cased.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((72, 72), "Hello PDF")
    doc.save(path)
    doc.close()

    hits = PdfReader().search(path, "hello")
    assert len(hits) >= 1
    assert hits[0].text != "hello"
    assert "Hello" in hits[0].text


def test_search_empty_query(sample_pdf: Path):
    assert PdfReader().search(sample_pdf, "   ") == []
