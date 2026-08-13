from app.domain.models import (
    ConversionRequest,
    OutputFormat,
    PageEdits,
    Point,
    StampKind,
    Stroke,
)


def test_output_format_values():
    assert OutputFormat.PNG == "png"
    assert OutputFormat("jpeg") is OutputFormat.JPEG


def test_conversion_request_defaults():
    req = ConversionRequest(format=OutputFormat.PNG)
    assert req.dpi == 150
    assert req.quality == 90


def test_page_edits_model():
    stroke = Stroke(
        points=(Point(0.1, 0.2), Point(0.3, 0.4)),
        color="#c0392b",
        width=0.01,
    )
    page = PageEdits(page_index=0, strokes=(stroke,))
    assert page.page_index == 0
    assert len(page.strokes[0].points) == 2
    assert StampKind.APPROVED == "approved"
