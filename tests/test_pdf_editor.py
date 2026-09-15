from pathlib import Path

import pymupdf
import pytest

from app.domain.models import (
    HighlightBox,
    PageEdits,
    Point,
    StampKind,
    StampMark,
    Stroke,
    TextBox,
)
from app.services.pdf_editor import PdfEditor, hex_to_rgb


def test_hex_to_rgb():
    assert hex_to_rgb("#ff0000") == (1.0, 0.0, 0.0)
    assert hex_to_rgb("00ff00") == (0.0, 1.0, 0.0)


def test_hex_to_rgb_invalid():
    with pytest.raises(ValueError):
        hex_to_rgb("#fff")


def test_apply_edits_writes_output(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "inked.pdf"
    strokes = PageEdits(
        page_index=0,
        strokes=(
            Stroke(
                points=(Point(0.1, 0.1), Point(0.5, 0.5), Point(0.9, 0.2)),
                color="#c0392b",
                width=0.01,
            ),
        ),
    )
    result = PdfEditor().apply_edits(sample_pdf, [strokes], out)
    assert result == out
    assert out.exists()


def test_apply_edits_text_highlight_stamp(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "edited.pdf"
    edits = PageEdits(
        page_index=0,
        texts=(TextBox(x=0.2, y=0.3, text="Nota", color="#111111", size=0.04),),
        highlights=(HighlightBox(0.1, 0.1, 0.5, 0.2, "#f1c40f"),),
        stamps=(StampMark(StampKind.APPROVED, 0.7, 0.7),),
    )
    PdfEditor().apply_edits(sample_pdf, [edits], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_rotate_page(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "rotated.pdf"
    PdfEditor().rotate_page(sample_pdf, 0, 90, out)
    with pymupdf.open(out) as doc:
        assert doc[0].rotation % 360 == 90


def test_rotate_invalid_degrees(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError, match="degrees must be"):
        PdfEditor().rotate_page(sample_pdf, 0, 45, tmp_path / "bad.pdf")


def test_rotate_page_out_of_range(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(IndexError):
        PdfEditor().rotate_page(sample_pdf, 3, 90, tmp_path / "bad.pdf")


def test_apply_edits_skips_noop_shapes(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "noop.pdf"
    edits = PageEdits(
        page_index=0,
        strokes=(Stroke(points=(Point(0.1, 0.1),), color="#000000", width=0.01),),
        texts=(TextBox(x=0.2, y=0.3, text="   ", color="#111111", size=0.04),),
        highlights=(HighlightBox(0.1, 0.1, 0.1005, 0.1005, "#f1c40f"),),
        stamps=(StampMark(StampKind.DATE, 0.5, 0.5), StampMark(StampKind.PAID, 0.6, 0.6)),
    )
    PdfEditor().apply_edits(sample_pdf, [edits], out)
    assert out.exists()

def test_extract_pages_writes_subset(multipage_pdf: Path, tmp_path: Path):
    out = tmp_path / "subset.pdf"
    PdfEditor().extract_pages(multipage_pdf, 1, 2, out)
    with pymupdf.open(out) as doc:
        assert len(doc) == 2
        assert "page 2" in doc[0].get_text()
        assert "page 3" in doc[1].get_text()


def test_extract_pages_invalid_range(multipage_pdf: Path, tmp_path: Path):
    with pytest.raises(IndexError):
        PdfEditor().extract_pages(multipage_pdf, 2, 1, tmp_path / "bad.pdf")


def test_extract_pages_out_of_range(multipage_pdf: Path, tmp_path: Path):
    with pytest.raises(IndexError):
        PdfEditor().extract_pages(multipage_pdf, 0, 10, tmp_path / "bad.pdf")


def test_apply_edits_page_out_of_range(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "bad.pdf"
    strokes = PageEdits(
        page_index=5,
        strokes=(
            Stroke(points=(Point(0.1, 0.1), Point(0.2, 0.2)), color="#000000", width=0.01),
        ),
    )
    with pytest.raises(IndexError):
        PdfEditor().apply_edits(sample_pdf, [strokes], out)
