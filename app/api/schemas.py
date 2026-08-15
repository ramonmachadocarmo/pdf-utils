from pydantic import BaseModel, Field, model_validator

from app.domain.models import StampKind


class PointIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class StrokeIn(BaseModel):
    color: str
    width: float = Field(gt=0, le=0.05)
    points: list[PointIn] = Field(min_length=2)


class TextBoxIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    text: str = Field(min_length=1, max_length=500)
    color: str = "#1c2420"
    size: float = Field(default=0.03, gt=0.005, le=0.2)


class HighlightBoxIn(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    color: str = "#f1c40f"


class StampIn(BaseModel):
    kind: StampKind
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PageEditsIn(BaseModel):
    page_index: int = Field(ge=0)
    strokes: list[StrokeIn] = Field(default_factory=list)
    texts: list[TextBoxIn] = Field(default_factory=list)
    highlights: list[HighlightBoxIn] = Field(default_factory=list)
    stamps: list[StampIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_edits(self):
        if not (self.strokes or self.texts or self.highlights or self.stamps):
            raise ValueError("page has no edits")
        return self


class AnnotateBody(BaseModel):
    pages: list[PageEditsIn] = Field(min_length=1)


class RotateBody(BaseModel):
    page_index: int = Field(ge=0)
    degrees: int = Field(default=90)
