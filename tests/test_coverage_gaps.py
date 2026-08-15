from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas import AnnotateBody, PageEditsIn
from app.main import app
from app.services.converter import ImageConverter
from app.domain.models import ConversionRequest, OutputFormat

client = TestClient(app)


def _upload(sample_pdf: Path) -> str:
    with sample_pdf.open("rb") as f:
        res = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    assert res.status_code == 200
    return res.json()["job_id"]


def test_job_not_found_endpoints():
    assert client.get("/api/preview/missing/0").status_code == 404
    assert client.get("/api/search/missing", params={"q": "x"}).status_code == 404
    assert client.post("/api/annotate/missing", json={"pages": [{"page_index": 0, "stamps": [{"kind": "paid", "x": 0.5, "y": 0.5}]}]}).status_code == 404
    assert client.post("/api/rotate/missing", json={"page_index": 0, "degrees": 90}).status_code == 404
    assert client.get("/api/download/missing").status_code == 404
    assert client.post("/api/convert/missing", data={"format": "png", "dpi": "72", "quality": "90"}).status_code == 404


def test_preview_page_out_of_range(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    res = client.get(f"/api/preview/{job_id}/99")
    assert res.status_code == 400


def test_annotate_page_out_of_range(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    res = client.post(
        f"/api/annotate/{job_id}",
        json={
            "pages": [
                {
                    "page_index": 9,
                    "stamps": [{"kind": "approved", "x": 0.5, "y": 0.5}],
                }
            ]
        },
    )
    assert res.status_code == 400


def test_annotate_unexpected_error(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    with patch("app.api.routes.editor.apply_edits", side_effect=RuntimeError("boom")):
        res = client.post(
            f"/api/annotate/{job_id}",
            json={"pages": [{"page_index": 0, "stamps": [{"kind": "paid", "x": 0.4, "y": 0.4}]}]},
        )
    assert res.status_code == 500
    assert "failed to annotate" in res.json()["detail"]


def test_rotate_invalid_degrees(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    res = client.post(f"/api/rotate/{job_id}", json={"page_index": 0, "degrees": 45})
    assert res.status_code == 400


def test_rotate_page_out_of_range(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    res = client.post(f"/api/rotate/{job_id}", json={"page_index": 5, "degrees": 90})
    assert res.status_code == 400


def test_rotate_unexpected_error(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    with patch("app.api.routes.editor.rotate_page", side_effect=RuntimeError("boom")):
        res = client.post(f"/api/rotate/{job_id}", json={"page_index": 0, "degrees": 90})
    assert res.status_code == 500
    assert "failed to rotate" in res.json()["detail"]


def test_convert_invalid_format(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    res = client.post(
        f"/api/convert/{job_id}",
        data={"format": "gif", "dpi": "72", "quality": "90"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "invalid format"


def test_convert_dpi_and_quality_bounds(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    low_dpi = client.post(
        f"/api/convert/{job_id}",
        data={"format": "png", "dpi": "10", "quality": "90"},
    )
    assert low_dpi.status_code == 400
    bad_q = client.post(
        f"/api/convert/{job_id}",
        data={"format": "jpeg", "dpi": "72", "quality": "0"},
    )
    assert bad_q.status_code == 400


def test_convert_cleans_previous_output(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    first = client.post(
        f"/api/convert/{job_id}",
        data={"format": "png", "dpi": "72", "quality": "90"},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/convert/{job_id}",
        data={"format": "jpeg", "dpi": "72", "quality": "80"},
    )
    assert second.status_code == 200
    assert second.headers["content-type"].startswith("image/jpeg")


def test_convert_unexpected_error(sample_pdf: Path):
    job_id = _upload(sample_pdf)
    with patch("app.api.routes.converter.convert", side_effect=RuntimeError("boom")):
        res = client.post(
            f"/api/convert/{job_id}",
            data={"format": "png", "dpi": "72", "quality": "90"},
        )
    assert res.status_code == 500
    assert "conversion failed" in res.json()["detail"]


def test_page_edits_require_content():
    with pytest.raises(ValidationError):
        PageEditsIn(page_index=0)


def test_annotate_body_rejects_empty_page():
    with pytest.raises(ValidationError):
        AnnotateBody.model_validate({"pages": [{"page_index": 0}]})


def test_image_converter_rejects_docx_as_image(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError, match="unsupported image format"):
        ImageConverter().convert(
            sample_pdf,
            tmp_path / "out",
            ConversionRequest(format=OutputFormat.DOCX, dpi=72),
        )


def test_locales_served():
    for locale in ("en", "pt-BR", "es"):
        res = client.get(f"/static/i18n/{locale}.json")
        assert res.status_code == 200
        data = res.json()
        assert "home.headline" in data


def test_index_has_i18n_hooks():
    res = client.get("/")
    assert res.status_code == 200
    assert b'data-i18n="home.headline"' in res.content
    assert b"/static/i18n.js" in res.content
    assert b'lang="en"' in res.content
