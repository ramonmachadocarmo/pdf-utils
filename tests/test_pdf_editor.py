from pathlib import Path

import pymupdf
import pytest

from app.domain.models import PageStrokes, Point, Stroke
from app.services.pdf_editor import PdfEditor, _hex_to_rgb


def test_hex_to_rgb():
    assert _hex_to_rgb("#ff0000") == (1.0, 0.0, 0.0)
    assert _hex_to_rgb("00ff00") == (0.0, 1.0, 0.0)


def test_hex_to_rgb_invalid():
    with pytest.raises(ValueError):
        _hex_to_rgb("#fff")


def test_apply_ink_writes_output(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "inked.pdf"
    strokes = PageStrokes(
        page_index=0,
        strokes=(
            Stroke(
                points=(Point(0.1, 0.1), Point(0.5, 0.5), Point(0.9, 0.2)),
                color="#c0392b",
                width=0.01,
            ),
        ),
    )

    result = PdfEditor().apply_ink(sample_pdf, [strokes], out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0

    with pymupdf.open(out) as doc:
        assert len(doc) == 1


def test_apply_ink_page_out_of_range(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "bad.pdf"
    strokes = PageStrokes(
        page_index=5,
        strokes=(
            Stroke(points=(Point(0.1, 0.1), Point(0.2, 0.2)), color="#000000", width=0.01),
        ),
    )
    with pytest.raises(IndexError):
        PdfEditor().apply_ink(sample_pdf, [strokes], out)
