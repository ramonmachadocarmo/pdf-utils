import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.api.schemas import AnnotateBody
from app.config import OUTPUTS, UPLOADS
from app.domain.models import ConversionRequest, OutputFormat, PageStrokes, Point, Stroke
from app.services.converter import ConversionService
from app.services.pdf_editor import PdfEditor
from app.services.pdf_reader import PdfReader

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


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "envie um arquivo PDF")

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
        raise HTTPException(404, "job nao encontrado")

    try:
        png = reader.render_page(pdf_path, page_index, dpi=dpi)
    except IndexError as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(content=png, media_type="image/png")


@router.post("/annotate/{job_id}")
async def annotate(job_id: str, body: AnnotateBody):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job nao encontrado")

    pages = [
        PageStrokes(
            page_index=page.page_index,
            strokes=tuple(
                Stroke(
                    points=tuple(Point(x=p.x, y=p.y) for p in stroke.points),
                    color=stroke.color,
                    width=stroke.width,
                )
                for stroke in page.strokes
            ),
        )
        for page in body.pages
    ]

    working = UPLOADS / job_id / "working.pdf"
    tmp_path = UPLOADS / job_id / "working.tmp.pdf"
    try:
        editor.apply_ink(pdf_path, pages, tmp_path)
        tmp_path.replace(working)
    except (IndexError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"falha ao anotar: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"ok": True, "job_id": job_id}


@router.get("/download/{job_id}")
async def download(job_id: str):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job nao encontrado")
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
        raise HTTPException(404, "job nao encontrado")

    try:
        output_format = OutputFormat(format.lower())
    except ValueError as exc:
        raise HTTPException(400, "formato invalido") from exc

    if dpi < 72 or dpi > 600:
        raise HTTPException(400, "dpi deve estar entre 72 e 600")
    if quality < 1 or quality > 100:
        raise HTTPException(400, "quality deve estar entre 1 e 100")

    out_dir = OUTPUTS / job_id / "convert"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    request = ConversionRequest(format=output_format, dpi=dpi, quality=quality)
    try:
        result = converter.convert(pdf_path, out_dir, request)
    except Exception as exc:
        raise HTTPException(500, f"falha na conversao: {exc}") from exc

    media = _MEDIA_TYPES.get(result.suffix.lower(), "application/octet-stream")
    return FileResponse(result, media_type=media, filename=result.name)
