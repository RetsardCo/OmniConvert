"""PDF processing engine: text extraction, metadata inspection, image-to-pdf, and splitting/merging."""

from pathlib import Path
import json
import logging
from typing import Callable, Optional, Dict, Any, List
import pypdf
from PIL import Image

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

logger = logging.getLogger(__name__)

class PDFEngine(BaseEngine):
    """Engine handling PDF inspection, text extraction, page manipulation, and image-to-PDF."""

    @property
    def name(self) -> str:
        return "pypdf"

    def is_available(self) -> bool:
        try:
            import pypdf
            return True
        except ImportError:
            return False

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if not self.is_available():
            raise RuntimeError("pypdf is not available.")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled before start.")

        source = job.source_path
        target_format = job.target_format.lower().lstrip(".")
        settings = job.settings or {}

        # 1. Image to PDF
        if job.operation_id == "image.to_pdf" or source.suffix.lower().lstrip(".") in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
            return self._image_to_pdf(source, workspace_dir, settings, progress_callback, is_cancelled)

        # 2. PDF operations
        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Reading PDF", detail=f"Parsing {source.name}"))

        try:
            reader = pypdf.PdfReader(str(source))
        except Exception as e:
            raise ValueError(f"Could not open or decrypt PDF: {e}")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF document contains 0 pages.")

        # PDF to TXT (Text extraction)
        if job.operation_id == "pdf.extract_text" or target_format == "txt":
            target_file = workspace_dir / f"{source.stem}.txt"
            extracted_text = []

            for i, page in enumerate(reader.pages):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during text extraction.")
                text = page.extract_text() or ""
                extracted_text.append(f"--- Page {i + 1} ---\n{text}")

                if progress_callback:
                    progress_callback(JobProgress(
                        percentage=int(10 + (i / total_pages) * 80),
                        stage="Extracting Text",
                        detail=f"Page {i + 1}/{total_pages}"
                    ))

            with open(target_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(extracted_text))

            if progress_callback:
                progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Text extracted"))

            return target_file

        # PDF to JSON (Structured metadata and page text extraction)
        elif job.operation_id == "pdf.to_json" or target_format == "json":
            target_file = workspace_dir / f"{source.stem}.json"
            meta = reader.metadata or {}

            doc_data = {
                "filename": source.name,
                "page_count": total_pages,
                "metadata": {
                    "title": meta.get("/Title"),
                    "author": meta.get("/Author"),
                    "subject": meta.get("/Subject"),
                    "creator": meta.get("/Creator"),
                    "producer": meta.get("/Producer"),
                },
                "pages": []
            }

            for i, page in enumerate(reader.pages):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during JSON export.")
                doc_data["pages"].append({
                    "page_number": i + 1,
                    "text": page.extract_text() or ""
                })

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(doc_data, f, indent=2)

            return target_file

        raise NotImplementedError(f"Unsupported PDF operation: {job.operation_id}")

    def _image_to_pdf(
        self,
        image_path: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable],
        is_cancelled: Optional[Callable]
    ) -> Path:
        """Wrap image into a clean single-page or multi-page PDF."""
        target_file = workspace_dir / f"{image_path.stem}.pdf"

        if progress_callback:
            progress_callback(JobProgress(percentage=30.0, stage="Converting Image", detail="Compositing image into PDF"))

        with Image.open(image_path) as img:
            # Convert RGBA to RGB with white background
            if img.mode != "RGB":
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[3])
                else:
                    rgb_img.paste(img.convert("RGB"))
                rgb_img.save(target_file, "PDF", resolution=100.0)
            else:
                img.save(target_file, "PDF", resolution=100.0)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Image saved as PDF"))

        return target_file

    def merge_pdfs(self, pdf_paths: List[Path], output_path: Path) -> Path:
        """Merge multiple PDF files into one combined PDF."""
        writer = pypdf.PdfWriter()
        for p in pdf_paths:
            writer.append(str(p))
        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()
        return output_path
