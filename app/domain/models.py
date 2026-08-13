from enum import StrEnum
from dataclasses import dataclass


class OutputFormat(StrEnum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    DOCX = "docx"


class StampKind(StrEnum):
    APPROVED = "approved"
    PAID = "paid"
    DATE = "date"


@dataclass(frozen=True)
class ConversionRequest:
    format: OutputFormat
    dpi: int = 150
    quality: int = 90


@dataclass(frozen=True)
class PageInfo:
    index: int
    width: float
    height: float


@dataclass(frozen=True)
class PdfMeta:
    page_count: int
    title: str
    pages: tuple[PageInfo, ...]


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Stroke:
    points: tuple[Point, ...]
    color: str
    width: float


@dataclass(frozen=True)
class TextBox:
    x: float
    y: float
    text: str
    color: str
    size: float


@dataclass(frozen=True)
class HighlightBox:
    x0: float
    y0: float
    x1: float
    y1: float
    color: str


@dataclass(frozen=True)
class StampMark:
    kind: StampKind
    x: float
    y: float


@dataclass(frozen=True)
class PageEdits:
    page_index: int
    strokes: tuple[Stroke, ...] = ()
    texts: tuple[TextBox, ...] = ()
    highlights: tuple[HighlightBox, ...] = ()
    stamps: tuple[StampMark, ...] = ()


@dataclass(frozen=True)
class SearchHit:
    page_index: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
