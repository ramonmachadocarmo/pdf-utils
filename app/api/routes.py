import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.api.schemas import AnnotateBody, MergeExecuteBody, RotateBody
from app.config import MAX_UPLOAD_SIZE, OUTPUTS, UPLOADS
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
from app.services.xml_converter import InvalidXmlError, XmlConverter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

reader = PdfReader()
converter = ConversionService()
editor = PdfEditor()
xml_converter = XmlConverter()

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


_ALLOWED_UPLOAD_SUFFIXES = (".pdf", ".xml")


def _convert_xml_source(xml_path: Path, upload_dir: Path, job_id: str, source_name: str) -> None:
    pdf_path = upload_dir / "source.pdf"
    try:
        xml_converter.convert(xml_path, pdf_path, source_name=source_name)
    except InvalidXmlError as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    except Exception:
        logger.exception("failed to convert XML for job %s", job_id)
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(500, "failed to convert XML") from None
    finally:
        xml_path.unlink(missing_ok=True)


def _finish_ingest(upload_dir: Path, job_id: str, filename: str) -> dict:
    pdf_path = upload_dir / "source.pdf"
    working_path = upload_dir / "working.pdf"
    shutil.copy2(pdf_path, working_path)

    meta = reader.read_meta(working_path)
    return {
        "job_id": job_id,
        "filename": filename,
        "title": meta.title,
        "page_count": meta.page_count,
        "pages": [
            {"index": p.index, "width": p.width, "height": p.height} for p in meta.pages
        ],
    }


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(400, "send a PDF or XML file")

    job_id = uuid.uuid4().hex
    upload_dir, _ = _job_dirs(job_id)
    raw_path = upload_dir / f"source{suffix}"

    size = 0
    exceeded = False
    with raw_path.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                exceeded = True
                break
            f.write(chunk)

    if exceeded:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(413, f"file exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit")

    if suffix == ".xml":
        _convert_xml_source(raw_path, upload_dir, job_id, file.filename)

    return _finish_ingest(upload_dir, job_id, file.filename)


def _round_size(width: float, height: float) -> tuple[float, float]:
    return (round(width, 1), round(height, 1))


@router.post("/merge/inspect")
async def merge_inspect(files: list[UploadFile] = File(...), current_job_id: str | None = Form(None)):
    min_required = 1 if current_job_id else 2
    if len(files) < min_required:
        raise HTTPException(400, "select at least two PDF files")
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "all files must be PDFs")

    merge_id = uuid.uuid4().hex
    input_dir = UPLOADS / merge_id / "merge_inputs"
    input_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    names: list[str] = []
    next_index = 0

    if current_job_id:
        current_pdf = _pdf_path(current_job_id)
        if not current_pdf.exists():
            shutil.rmtree(input_dir.parent, ignore_errors=True)
            raise HTTPException(404, "current document not found")
        dest = input_dir / f"{next_index:03d}.pdf"
        shutil.copy2(current_pdf, dest)
        saved.append(dest)
        names.append("current document")
        next_index += 1

    for f in files:
        dest = input_dir / f"{next_index:03d}.pdf"
        size = 0
        exceeded = False
        with dest.open("wb") as out:
            while chunk := await f.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    exceeded = True
                    break
                out.write(chunk)
        if exceeded:
            shutil.rmtree(input_dir.parent, ignore_errors=True)
            raise HTTPException(413, f"each file must be under {MAX_UPLOAD_SIZE // (1024 * 1024)}MB")
        saved.append(dest)
        names.append(f.filename)
        next_index += 1

    size_counts: dict[tuple[float, float], int] = {}
    file_infos = []
    for path, name in zip(saved, names):
        try:
            meta = reader.read_meta(path)
        except Exception:
            shutil.rmtree(input_dir.parent, ignore_errors=True)
            raise HTTPException(400, f"could not read {name}") from None
        for p in meta.pages:
            key = _round_size(p.width, p.height)
            size_counts[key] = size_counts.get(key, 0) + 1
        file_infos.append({"name": name, "page_count": meta.page_count})

    sizes = [
        {"width": w, "height": h, "page_count": count}
        for (w, h), count in sorted(size_counts.items(), key=lambda kv: -kv[1])
    ]

    return {
        "merge_id": merge_id,
        "files": file_infos,
        "sizes": sizes,
        "uniform": len(sizes) <= 1,
    }


@router.post("/merge/execute")
async def merge_execute(body: MergeExecuteBody):
    input_dir = UPLOADS / body.merge_id / "merge_inputs"
    if not input_dir.exists():
        raise HTTPException(404, "merge session not found")

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    if len(pdf_paths) < 2:
        raise HTTPException(400, "merge session is missing files")

    job_id = uuid.uuid4().hex
    upload_dir, _ = _job_dirs(job_id)
    pdf_path = upload_dir / "source.pdf"

    try:
        editor.merge_pdfs(pdf_paths, body.width, body.height, pdf_path)
    except Exception:
        logger.exception("failed to merge session %s", body.merge_id)
        raise HTTPException(500, "failed to merge PDFs") from None
    finally:
        shutil.rmtree(input_dir.parent, ignore_errors=True)

    return _finish_ingest(upload_dir, job_id, "merged.pdf")


@router.post("/open-local")
async def open_local(path: str):
    """Load a PDF or XML already on disk, used when the desktop app is launched via file association."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_SUFFIXES or not source.is_file():
        raise HTTPException(400, "file not found")

    if source.stat().st_size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"file exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit")

    job_id = uuid.uuid4().hex
    upload_dir, _ = _job_dirs(job_id)
    raw_path = upload_dir / f"source{suffix}"
    try:
        shutil.copy2(source, raw_path)
    except OSError as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(400, "could not read file") from exc

    if suffix == ".xml":
        _convert_xml_source(raw_path, upload_dir, job_id, source.name)

    return _finish_ingest(upload_dir, job_id, source.name)


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


@router.get("/text/{job_id}")
async def extract_text(job_id: str, page_index: int | None = None):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    try:
        text = reader.extract_text(pdf_path, page_index)
    except IndexError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"text": text}


@router.get("/print/{job_id}")
async def print_pages(job_id: str, start: int, end: int | None = None):
    pdf_path = _pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(404, "job not found")

    out_path = OUTPUTS / job_id / "print.pdf"
    try:
        editor.extract_pages(pdf_path, start, end if end is not None else start, out_path)
    except IndexError as exc:
        raise HTTPException(400, str(exc)) from exc

    return FileResponse(out_path, media_type="application/pdf", filename="print.pdf")


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
    except Exception:
        logger.exception("failed to annotate job %s", job_id)
        raise HTTPException(500, "failed to annotate PDF") from None
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
    except Exception:
        logger.exception("failed to rotate job %s", job_id)
        raise HTTPException(500, "failed to rotate PDF") from None
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
    except Exception:
        logger.exception("conversion failed for job %s", job_id)
        raise HTTPException(500, "conversion failed") from None

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
