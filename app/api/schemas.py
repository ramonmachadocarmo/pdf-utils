from pydantic import BaseModel, Field


class PointIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class StrokeIn(BaseModel):
    color: str
    width: float = Field(gt=0, le=0.05)
    points: list[PointIn] = Field(min_length=2)


class PageStrokesIn(BaseModel):
    page_index: int = Field(ge=0)
    strokes: list[StrokeIn] = Field(min_length=1)


class AnnotateBody(BaseModel):
    pages: list[PageStrokesIn] = Field(min_length=1)
