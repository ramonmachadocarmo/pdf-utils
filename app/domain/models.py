from enum import StrEnum
from dataclasses import dataclass


class OutputFormat(StrEnum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    DOCX = "docx"


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
class PageStrokes:
    page_index: int
    strokes: tuple[Stroke, ...]
