from pathlib import Path
from zipfile import ZipFile

import pymupdf

from app.domain.models import ConversionRequest, OutputFormat


class ImageConverter:
    def convert(self, pdf_path: Path, out_dir: Path, request: ConversionRequest) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        fmt = request.format.value
        matrix = pymupdf.Matrix(request.dpi / 72, request.dpi / 72)
        outputs: list[Path] = []

        with pymupdf.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                target = out_dir / f"page_{i + 1:04d}.{fmt if fmt != 'jpeg' else 'jpg'}"
                if fmt == "png":
                    pix.save(target.as_posix())
                elif fmt == "jpeg":
                    pix.pil_save(target.as_posix(), format="JPEG", quality=request.quality)
                elif fmt == "webp":
                    pix.pil_save(target.as_posix(), format="WEBP", quality=request.quality)
                else:
                    raise ValueError(f"unsupported image format: {fmt}")
                outputs.append(target)

        return outputs

    def zip_outputs(self, files: list[Path], zip_path: Path) -> Path:
        with ZipFile(zip_path, "w") as zf:
            for file in files:
                zf.write(file, arcname=file.name)
        return zip_path


class DocxConverter:
    def convert(self, pdf_path: Path, out_path: Path) -> Path:
        from pdf2docx import Converter

        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv = Converter(pdf_path.as_posix())
        try:
            cv.convert(out_path.as_posix())
        finally:
            cv.close()
        return out_path


class ConversionService:
    def __init__(self) -> None:
        self._images = ImageConverter()
        self._docx = DocxConverter()

    def convert(self, pdf_path: Path, work_dir: Path, request: ConversionRequest) -> Path:
        if request.format == OutputFormat.DOCX:
            return self._docx.convert(pdf_path, work_dir / f"{pdf_path.stem}.docx")

        images = self._images.convert(pdf_path, work_dir / "pages", request)
        if len(images) == 1:
            return images[0]

        return self._images.zip_outputs(images, work_dir / f"{pdf_path.stem}_{request.format.value}.zip")
