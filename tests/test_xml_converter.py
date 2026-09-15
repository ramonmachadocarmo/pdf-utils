import time
from pathlib import Path

import pymupdf
import pytest

from app.services.xml_converter import InvalidXmlError, XmlConverter

_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe12345" versao="4.00">
    <ide><nNF>1234</nNF></ide>
    <emit><xNome>ACME LTDA</xNome></emit>
  </infNFe>
</NFe>
"""


def test_convert_renders_readable_pdf(tmp_path: Path):
    xml_path = tmp_path / "nfe.xml"
    xml_path.write_text(_SAMPLE_XML, encoding="utf-8")

    out = XmlConverter().convert(xml_path, tmp_path / "out.pdf")

    assert out.exists()
    with pymupdf.open(out) as doc:
        assert len(doc) >= 1
        text = doc[0].get_text()
    assert "NFe" in text
    assert "ACME LTDA" in text
    assert "1234" in text


def test_convert_paginates_large_documents(tmp_path: Path):
    items = "".join(f"<item id='{i}'>value {i}</item>" for i in range(2000))
    xml_path = tmp_path / "big.xml"
    xml_path.write_text(f"<root>{items}</root>", encoding="utf-8")

    out = XmlConverter().convert(xml_path, tmp_path / "out.pdf")

    with pymupdf.open(out) as doc:
        assert len(doc) > 1
        full_text = "".join(page.get_text() for page in doc)
    # Regression guard: mupdf's Story engine silently stops paginating (reporting
    # a page as complete while later content overflows off-page, undetected) once
    # a repeated-content document needs several pages, if any element sets an
    # explicit font-size. Check the tail item actually made it onto a page.
    assert "value 0" in full_text
    assert "value 1999" in full_text


def test_convert_truncates_huge_text_node(tmp_path: Path):
    blob = "\n".join("A" * 76 for _ in range(20_000))  # ~1.5 MB, like an embedded CRL
    xml_path = tmp_path / "signed.xml"
    xml_path.write_text(f"<root><EncapsulatedCRLValue>{blob}</EncapsulatedCRLValue></root>", encoding="utf-8")

    start = time.monotonic()
    out = XmlConverter().convert(xml_path, tmp_path / "out.pdf")
    elapsed = time.monotonic() - start

    assert elapsed < 10, "conversion should not stall laying out oversized text blobs"
    with pymupdf.open(out) as doc:
        assert len(doc) >= 1
        assert "truncated" in doc[0].get_text()


def test_css_has_no_font_size_overrides():
    # font-size on any selector reintroduces the silent-pagination-truncation bug
    # covered by test_convert_paginates_large_documents (see its comment).
    from app.services.xml_converter import _CSS

    assert "font-size" not in _CSS


def test_convert_rejects_malformed_xml(tmp_path: Path):
    xml_path = tmp_path / "bad.xml"
    xml_path.write_text("<not><closed>", encoding="utf-8")

    with pytest.raises(InvalidXmlError):
        XmlConverter().convert(xml_path, tmp_path / "out.pdf")


def test_convert_rejects_xxe(tmp_path: Path):
    xml_path = tmp_path / "xxe.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        "<foo>&xxe;</foo>",
        encoding="utf-8",
    )

    with pytest.raises(InvalidXmlError):
        XmlConverter().convert(xml_path, tmp_path / "out.pdf")


def test_convert_rejects_entity_expansion_bomb(tmp_path: Path):
    xml_path = tmp_path / "bomb.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>'
        "<lolz>&lol2;</lolz>",
        encoding="utf-8",
    )

    with pytest.raises(InvalidXmlError):
        XmlConverter().convert(xml_path, tmp_path / "out.pdf")
