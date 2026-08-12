from pathlib import Path
from zipfile import ZipFile

import pytest

from app.domain.models import ConversionRequest, OutputFormat
from app.services.converter import ConversionService, ImageConverter


def test_convert_single_page_png(sample_pdf: Path, tmp_path: Path):
    out = ConversionService().convert(
        sample_pdf,
        tmp_path / "work",
        ConversionRequest(format=OutputFormat.PNG, dpi=72),
    )
    assert out.suffix == ".png"
    assert out.exists()
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_convert_jpeg(sample_pdf: Path, tmp_path: Path):
    out = ConversionService().convert(
        sample_pdf,
        tmp_path / "work",
        ConversionRequest(format=OutputFormat.JPEG, dpi=72, quality=80),
    )
    assert out.suffix == ".jpg"
    assert out.exists()


def test_convert_webp(sample_pdf: Path, tmp_path: Path):
    out = ConversionService().convert(
        sample_pdf,
        tmp_path / "work",
        ConversionRequest(format=OutputFormat.WEBP, dpi=72),
    )
    assert out.suffix == ".webp"
    assert out.exists()


def test_convert_multipage_zips(multipage_pdf: Path, tmp_path: Path):
    out = ConversionService().convert(
        multipage_pdf,
        tmp_path / "work",
        ConversionRequest(format=OutputFormat.PNG, dpi=72),
    )
    assert out.suffix == ".zip"
    with ZipFile(out) as zf:
        names = zf.namelist()
    assert names == ["page_0001.png", "page_0002.png", "page_0003.png"]


def test_zip_outputs(tmp_path: Path):
    files = []
    for i in range(2):
        f = tmp_path / f"f{i}.txt"
        f.write_text("x")
        files.append(f)
    zip_path = tmp_path / "out.zip"
    result = ImageConverter().zip_outputs(files, zip_path)
    assert result == zip_path
    with ZipFile(zip_path) as zf:
        assert set(zf.namelist()) == {"f0.txt", "f1.txt"}


def test_docx_convert_uses_pdf2docx(sample_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: dict[str, object] = {}

    class FakeConverter:
        def __init__(self, path: str):
            calls["in"] = path

        def convert(self, out: str):
            calls["out"] = out
            Path(out).write_bytes(b"docx")

        def close(self):
            calls["closed"] = True

    monkeypatch.setattr("pdf2docx.Converter", FakeConverter)

    out = ConversionService().convert(
        sample_pdf,
        tmp_path / "work",
        ConversionRequest(format=OutputFormat.DOCX),
    )
    assert out.name == "sample.docx"
    assert out.read_bytes() == b"docx"
    assert calls["closed"] is True
