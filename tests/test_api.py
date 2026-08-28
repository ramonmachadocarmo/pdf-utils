from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.api import routes
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
                    "texts": [
                        {"x": 0.2, "y": 0.4, "text": "ok", "color": "#000000", "size": 0.03}
                    ],
                    "highlights": [
                        {"x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.2, "color": "#f1c40f"}
                    ],
                    "stamps": [{"kind": "approved", "x": 0.7, "y": 0.7}],
                }
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    dl = client.get(f"/api/download/{job_id}")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"


def test_search_and_rotate(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    search = client.get(f"/api/search/{job_id}", params={"q": "hello"})
    assert search.status_code == 200
    assert search.json()["count"] >= 1

    rotated = client.post(
        f"/api/rotate/{job_id}",
        json={"page_index": 0, "degrees": 90},
    )
    assert rotated.status_code == 200
    assert rotated.json()["ok"] is True


def test_convert_png(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    res = client.post(
        f"/api/convert/{job_id}",
        data={"format": "png", "dpi": "72", "quality": "90"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/png")


def test_upload_rejects_oversized_file(sample_pdf: Path, monkeypatch):
    monkeypatch.setattr(routes, "MAX_UPLOAD_SIZE", 10)
    with sample_pdf.open("rb") as f:
        res = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    assert res.status_code == 413


def test_open_local_loads_existing_file(sample_pdf: Path):
    res = client.post("/api/open-local", params={"path": str(sample_pdf)})
    assert res.status_code == 200
    data = res.json()
    assert data["page_count"] == 1
    assert data["filename"] == sample_pdf.name


def test_open_local_rejects_missing_file(tmp_path: Path):
    res = client.post("/api/open-local", params={"path": str(tmp_path / "missing.pdf")})
    assert res.status_code == 400


def test_open_local_rejects_non_pdf(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("nope")
    res = client.post("/api/open-local", params={"path": str(path)})
    assert res.status_code == 400


def test_open_local_rejects_oversized_file(sample_pdf: Path, monkeypatch):
    monkeypatch.setattr(routes, "MAX_UPLOAD_SIZE", 10)
    res = client.post("/api/open-local", params={"path": str(sample_pdf)})
    assert res.status_code == 413


def test_merge_inspect_rejects_single_file(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        res = client.post("/api/merge/inspect", files={"files": ("sample.pdf", f, "application/pdf")})
    assert res.status_code == 400


def test_merge_inspect_uniform_size(multipage_pdf: Path):
    with multipage_pdf.open("rb") as a, multipage_pdf.open("rb") as b:
        res = client.post(
            "/api/merge/inspect",
            files=[
                ("files", ("a.pdf", a, "application/pdf")),
                ("files", ("b.pdf", b, "application/pdf")),
            ],
        )
    assert res.status_code == 200
    data = res.json()
    assert data["uniform"] is True
    assert len(data["sizes"]) == 1
    assert data["sizes"][0]["page_count"] == 6


def test_merge_inspect_detects_mixed_sizes(sample_pdf: Path, multipage_pdf: Path):
    with sample_pdf.open("rb") as a, multipage_pdf.open("rb") as b:
        res = client.post(
            "/api/merge/inspect",
            files=[
                ("files", ("sample.pdf", a, "application/pdf")),
                ("files", ("multi.pdf", b, "application/pdf")),
            ],
        )
    assert res.status_code == 200
    data = res.json()
    assert data["uniform"] is False
    assert len(data["sizes"]) == 2


def test_merge_execute_resizes_mismatched_pages(sample_pdf: Path, multipage_pdf: Path):
    with sample_pdf.open("rb") as a, multipage_pdf.open("rb") as b:
        inspect = client.post(
            "/api/merge/inspect",
            files=[
                ("files", ("sample.pdf", a, "application/pdf")),
                ("files", ("multi.pdf", b, "application/pdf")),
            ],
        )
    merge_id = inspect.json()["merge_id"]

    res = client.post(
        "/api/merge/execute",
        json={"merge_id": merge_id, "width": 300, "height": 400},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["page_count"] == 4
    assert all(p["width"] == 300 and p["height"] == 400 for p in data["pages"])


def test_merge_inspect_appends_to_current_document(sample_pdf: Path, multipage_pdf: Path):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    current_job_id = up.json()["job_id"]

    with multipage_pdf.open("rb") as f:
        res = client.post(
            "/api/merge/inspect",
            data={"current_job_id": current_job_id},
            files=[("files", ("multi.pdf", f, "application/pdf"))],
        )
    assert res.status_code == 200
    data = res.json()
    assert data["uniform"] is False
    assert len(data["files"]) == 2

    execute = client.post(
        "/api/merge/execute",
        json={"merge_id": data["merge_id"], "width": 300, "height": 400},
    )
    assert execute.status_code == 200
    assert execute.json()["page_count"] == 4


def test_merge_inspect_rejects_unknown_current_document(sample_pdf: Path):
    with sample_pdf.open("rb") as f:
        res = client.post(
            "/api/merge/inspect",
            data={"current_job_id": "does-not-exist"},
            files=[("files", ("sample.pdf", f, "application/pdf"))],
        )
    assert res.status_code == 404


def test_merge_execute_rejects_unknown_merge_id():
    res = client.post(
        "/api/merge/execute",
        json={"merge_id": "does-not-exist", "width": 300, "height": 400},
    )
    assert res.status_code == 404


def test_annotate_internal_error_returns_generic_message(sample_pdf: Path, monkeypatch):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    def boom(*args, **kwargs):
        raise RuntimeError("internal detail: C:\\secret\\path")

    monkeypatch.setattr(routes.editor, "apply_edits", boom)
    res = client.post(
        f"/api/annotate/{job_id}",
        json={"pages": [{"page_index": 0, "stamps": [{"kind": "approved", "x": 0.5, "y": 0.5}]}]},
    )
    assert res.status_code == 500
    assert res.json()["detail"] == "failed to annotate PDF"
    assert "secret" not in res.text


def test_rotate_internal_error_returns_generic_message(sample_pdf: Path, monkeypatch):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    def boom(*args, **kwargs):
        raise RuntimeError("internal detail: C:\\secret\\path")

    monkeypatch.setattr(routes.editor, "rotate_page", boom)
    res = client.post(f"/api/rotate/{job_id}", json={"page_index": 0, "degrees": 90})
    assert res.status_code == 500
    assert res.json()["detail"] == "failed to rotate PDF"
    assert "secret" not in res.text


def test_convert_internal_error_returns_generic_message(sample_pdf: Path, monkeypatch):
    with sample_pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    job_id = up.json()["job_id"]

    def boom(*args, **kwargs):
        raise RuntimeError("internal detail: C:\\secret\\path")

    monkeypatch.setattr(routes.converter, "convert", boom)
    res = client.post(
        f"/api/convert/{job_id}",
        data={"format": "png", "dpi": "72", "quality": "90"},
    )
    assert res.status_code == 500
    assert res.json()["detail"] == "conversion failed"
    assert "secret" not in res.text


def test_index_page():
    res = client.get("/")
    assert res.status_code == 200
    assert b"PDF Utils" in res.content
    assert b'data-i18n="home.headline"' in res.content
