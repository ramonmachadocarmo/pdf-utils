import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.api.schemas import AnnotateBody, RotateBody
from app.config import OUTPUTS, UPLOADS
from app.domain.models import (
    ConversionRequest,
    HighlightBox,
    OutputFormat,
    PageEdits,
    Point,
    StampMark,
    Stroke,
    TextBox,
)
from app.services.converter import ConversionService
from app.services.pdf_editor import PdfEditor
from app.services.pdf_reader import PdfReader
from app.services.updater import check_for_update

router = APIRouter(prefix="/api")

reader = PdfReader()
converter = ConversionService()
editor = PdfEditor()

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".zip": "application/zip",
}


def _job_dirs(job_id: str) -> tuple[Path, Path]:
    upload = UPLOADS / job_id
    output = OUTPUTS / job_id
    upload.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    return upload, output


def _pdf_path(job_id: str) -> Path:
    working = UPLOADS / job_id / "working.pdf"
    source = UPLOADS / job_id / "source.pdf"
    return working if working.exists() else source


def _replace_working(job_id: str, tmp_path: Path) -> None:
    working = UPLOADS / job_id / "working.pdf"
    tmp_path.replace(working)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "send a PDF file")

    job_id = uuid.uuid4().hex
    upload_dir, _ = _job_dirs(job_id)
    pdf_path = upload_dir / "source.pdf"
    working_path = upload_dir / "working.pdf"

    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    shutil.copy2(pdf_path, working_path)

    meta = reader.read_meta(working_path)
    return {
        "job_id": job_id,
        "filename": file.filename,
        "title": meta.title,
        "page_count": meta.page_count,
        "pages": [
            {"index": p.index, "width": p.width, "height": p.height} for p in meta.pages
        ],
    }


@router.get("/preview/{job_id}/{page_index}")
async def preview(job_id: str, page_index: int, dpi: int = 120):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    try:
        png = reader.render_page(pdf_path, page_index, dpi=dpi)
    except IndexError as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(content=png, media_type="image/png")


@router.get("/search/{job_id}")
async def search(job_id: str, q: str = ""):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")
    hits = reader.search(pdf_path, q)
    return {
        "query": q,
        "count": len(hits),
        "hits": [
            {
                "page_index": h.page_index,
                "text": h.text,
                "x0": h.x0,
                "y0": h.y0,
                "x1": h.x1,
                "y1": h.y1,
            }
            for h in hits
        ],
    }


@router.post("/annotate/{job_id}")
async def annotate(job_id: str, body: AnnotateBody):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    pages = [
        PageEdits(
            page_index=page.page_index,
            strokes=tuple(
                Stroke(
                    points=tuple(Point(x=p.x, y=p.y) for p in stroke.points),
                    color=stroke.color,
                    width=stroke.width,
                )
                for stroke in page.strokes
            ),
            texts=tuple(
                TextBox(
                    x=t.x,
                    y=t.y,
                    text=t.text,
                    color=t.color,
                    size=t.size,
                )
                for t in page.texts
            ),
            highlights=tuple(
                HighlightBox(
                    x0=h.x0,
                    y0=h.y0,
                    x1=h.x1,
                    y1=h.y1,
                    color=h.color,
                )
                for h in page.highlights
            ),
            stamps=tuple(StampMark(kind=s.kind, x=s.x, y=s.y) for s in page.stamps),
        )
        for page in body.pages
    ]

    tmp_path = UPLOADS / job_id / "working.tmp.pdf"
    try:
        editor.apply_edits(pdf_path, pages, tmp_path)
        _replace_working(job_id, tmp_path)
    except (IndexError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"failed to annotate: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"ok": True, "job_id": job_id}


@router.post("/rotate/{job_id}")
async def rotate(job_id: str, body: RotateBody):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    tmp_path = UPLOADS / job_id / "working.tmp.pdf"
    try:
        editor.rotate_page(pdf_path, body.page_index, body.degrees, tmp_path)
        _replace_working(job_id, tmp_path)
    except (IndexError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"failed to rotate: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    meta = reader.read_meta(_pdf_path(job_id))
    return {"ok": True, "page_count": meta.page_count}


@router.get("/download/{job_id}")
async def download(job_id: str):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename="edited.pdf")


@router.post("/convert/{job_id}")
async def convert(
    job_id: str,
    format: str = Form(...),
    dpi: int = Form(150),
    quality: int = Form(90),
):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    try:
        output_format = OutputFormat(format.lower())
    except ValueError as exc:
        raise HTTPException(400, "invalid format") from exc

    if dpi < 72 or dpi > 600:
        raise HTTPException(400, "dpi must be between 72 and 600")
    if quality < 1 or quality > 100:
        raise HTTPException(400, "quality must be between 1 and 100")

    out_dir = OUTPUTS / job_id / "convert"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    request = ConversionRequest(format=output_format, dpi=dpi, quality=quality)
    try:
        result = converter.convert(pdf_path, out_dir, request)
    except Exception as exc:
        raise HTTPException(500, f"conversion failed: {exc}") from exc

    media = _MEDIA_TYPES.get(result.suffix.lower(), "application/octet-stream")
    return FileResponse(result, media_type=media, filename=result.name)


@router.get("/update-check")
def update_check():
    info = check_for_update()
    return {
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "update_available": info.update_available,
        "release_url": info.release_url,
        "download_url": info.download_url,
    }
