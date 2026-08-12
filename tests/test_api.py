from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.api.schemas import AnnotateBody, StrokeIn
from app.main import app


client = TestClient(app)


def test_stroke_schema_rejects_short_path():
    with pytest.raises(ValidationError):
        StrokeIn(color="#000000", width=0.01, points=[{"x": 0.1, "y": 0.1}])


def test_annotate_body_ok():
    body = AnnotateBody.model_validate(
        {
            "pages": [
                {
                    "page_index": 0,
                    "strokes": [
                        {
                            "color": "#c0392b",
                            "width": 0.01,
                            "points": [{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2}],
                        }
                    ],
                }
            ]
        }
    )
    assert body.pages[0].page_index == 0


def test_upload_and_preview(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        res = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    assert res.status_code == 200
    data = res.json()
    assert data["page_count"] == 1
    job_id = data["job_id"]

    preview = client.get(f"/api/preview/{job_id}/0")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")


def test_upload_rejects_non_pdf(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("nope")
    with path.open("rb") as f:
        res = client.post("/api/upload", files={"file": ("note.txt", f, "text/plain")})
    assert res.status_code == 400


def test_annotate_and_download(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    res = client.post(
        f"/api/annotate/{job_id}",
        json={
            "pages": [
                {
                    "page_index": 0,
                    "strokes": [
                        {
                            "color": "#111111",
                            "width": 0.01,
                            "points": [{"x": 0.1, "y": 0.1}, {"x": 0.8, "y": 0.8}],
                        }
                    ],
                }
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    dl = client.get(f"/api/download/{job_id}")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"
