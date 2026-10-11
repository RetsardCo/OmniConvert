"""PDF processing engine: PDF-to-Word (DOCX), text extraction, metadata, image-to-PDF, PDF-to-Image, HTML/MD export, and merging."""

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
    """Engine handling PDF-to-Word (DOCX), PDF inspection, text extraction, page rendering, and image-to-PDF."""

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
        op = job.operation_id

        # 0. Batch Images to Multi-Page PDF
        if op == "image.batch_to_pdf" or settings.get("batch_image_paths"):
            raw_paths = settings.get("batch_image_paths", [])
            paths = [Path(p) for p in raw_paths] if raw_paths else [source]
            target_name = settings.get("output_filename", f"{source.stem}_combined.pdf")
            return self.images_to_pdf(paths, workspace_dir / target_name, settings, progress_callback, is_cancelled)

        # 1. Image to PDF
        if op == "image.to_pdf" or source.suffix.lower().lstrip(".") in ("png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "heic", "heif"):
            return self._image_to_pdf(source, workspace_dir, settings, progress_callback, is_cancelled)

        # 2. PDF to Word (.docx)
        if op == "pdf.to_docx" or target_format == "docx":
            return self._pdf_to_docx(source, workspace_dir, settings, job, progress_callback, is_cancelled)

        # 3. PDF to Image (.png / .jpeg)
        if op in ("pdf.to_png", "pdf.to_jpeg") or target_format in ("png", "jpg", "jpeg"):
            return self._pdf_to_image(source, workspace_dir, target_format, settings, progress_callback, is_cancelled)

        # 4. PDF to HTML or Markdown
        if op == "pdf.to_html" or target_format == "html":
            return self._pdf_to_html(source, workspace_dir, settings, progress_callback, is_cancelled)
        if op == "pdf.to_md" or target_format in ("md", "markdown"):
            return self._pdf_to_markdown(source, workspace_dir, settings, progress_callback, is_cancelled)

        # 5. Standard PDF operations via pypdf / fitz
        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Reading PDF", detail=f"Parsing {source.name}"))

        try:
            reader = pypdf.PdfReader(str(source))
        except Exception as e:
            raise ValueError(f"Could not open or decrypt PDF: {e}")

        if reader.is_encrypted:
            password = settings.get("password", "")
            try:
                if reader.decrypt(password) == 0:
                    raise ValueError("PDF is password-protected and could not be decrypted.")
            except Exception as e:
                raise ValueError(f"Encrypted PDF cannot be opened without valid password: {e}")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF document contains 0 pages.")

        # PDF to TXT (Text extraction)
        if op == "pdf.extract_text" or target_format == "txt":
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
        elif op == "pdf.to_json" or target_format == "json":
            target_file = workspace_dir / f"{source.stem}.json"
            meta = reader.metadata or {}

            doc_data = {
                "filename": source.name,
                "page_count": total_pages,
                "metadata": {
                    "title": str(meta.get("/Title")) if meta.get("/Title") else None,
                    "author": str(meta.get("/Author")) if meta.get("/Author") else None,
                    "subject": str(meta.get("/Subject")) if meta.get("/Subject") else None,
                    "creator": str(meta.get("/Creator")) if meta.get("/Creator") else None,
                    "producer": str(meta.get("/Producer")) if meta.get("/Producer") else None,
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

        # PDF Page Split / Extract Pages to PDF
        elif op == "pdf.extract_pages" or target_format == "pdf":
            target_file = workspace_dir / f"{source.stem}.pdf"
            start_page = max(1, int(settings.get("start_page", 1) or 1))
            end_page_raw = int(settings.get("end_page", 0) or 0)
            end_page = total_pages if end_page_raw <= 0 else min(total_pages, end_page_raw)
            if start_page > end_page:
                raise ValueError(f"Invalid page range: start_page ({start_page}) > end_page ({end_page}).")

            writer = pypdf.PdfWriter()
            for idx in range(start_page - 1, end_page):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during PDF page extraction.")
                writer.add_page(reader.pages[idx])
            with open(target_file, "wb") as f:
                writer.write(f)
            writer.close()
            return target_file

        raise NotImplementedError(f"Unsupported PDF operation: {op}")

    def _pdf_to_docx(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        job: ConversionJob,
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """
        Convert PDF to an editable Microsoft Word (.docx) document.
        Supports quality presets:
        - 'lossless' / 'exact' / 'high': Full layout, tables, formatting, and embedded images via pdf2docx / PyMuPDF.
        - 'balanced': Structured paragraphs, tables, and embedded images.
        - 'compact': Fast text and paragraph reconstruction.
        """
        target_file = workspace_dir / f"{source.stem}.docx"
        preset = str(settings.get("quality_preset", "lossless")).lower()

        if progress_callback:
            progress_callback(JobProgress(percentage=15.0, stage="Analyzing PDF Layout", detail=f"Converting {source.name} to Word (.docx)"))

        # Validate PDF is readable and non-empty first
        try:
            reader = pypdf.PdfReader(str(source))
            if reader.is_encrypted:
                password = settings.get("password", "")
                if reader.decrypt(password) == 0:
                    raise ValueError("PDF is password-protected and could not be decrypted.")
            if len(reader.pages) == 0:
                raise ValueError("PDF document contains 0 pages.")
        except Exception as e:
            raise ValueError(f"Could not open source PDF: {e}")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before PDF-to-DOCX conversion.")

        used_layout_converter = False
        if preset in ("lossless", "exact", "high", "balanced"):
            try:
                from pdf2docx import Converter
                cv = Converter(str(source))
                try:
                    cv.convert(str(target_file), start=0, end=None)
                    used_layout_converter = True
                finally:
                    cv.close()
            except Exception as e:
                logger.warning("pdf2docx layout converter fallback triggered: %s", e)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled during PDF-to-DOCX conversion.")

        # Verify that target_file exists and has content; if pdf2docx didn't run or produced an empty doc on a image/blank PDF, enrich via python-docx + PyMuPDF
        try:
            import docx
            from docx.shared import Inches, Pt
            import fitz

            need_fallback = not used_layout_converter or not target_file.exists()
            if not need_fallback:
                # Check if document is readable by python-docx
                check_doc = docx.Document(str(target_file))
                has_any_content = (
                    any(p.text.strip() for p in check_doc.paragraphs)
                    or len(check_doc.tables) > 0
                    or len(check_doc.inline_shapes) > 0
                )
                if not has_any_content:
                    need_fallback = True

            if need_fallback:
                doc = docx.Document()
                pdf_doc = fitz.open(str(source))
                total_pages = len(pdf_doc)

                for page_idx in range(total_pages):
                    if is_cancelled and is_cancelled():
                        pdf_doc.close()
                        raise InterruptedError("Cancelled during PDF-to-DOCX conversion.")

                    page = pdf_doc[page_idx]
                    if page_idx > 0:
                        doc.add_page_break()

                    blocks = page.get_text("blocks")
                    has_text_on_page = False
                    for b in blocks:
                        # block tuple: (x0, y0, x1, y1, "text", block_no, block_type)
                        if len(b) >= 7 and b[6] == 0:
                            text_line = b[4].strip()
                            if text_line:
                                has_text_on_page = True
                                p = doc.add_paragraph(text_line)
                                p.style.font.size = Pt(11)

                    # Extract embedded images if in lossless/high/balanced mode, or render page image if scanned
                    if preset in ("lossless", "exact", "high", "balanced"):
                        img_list = page.get_images(full=True)
                        for img_idx, img_info in enumerate(img_list):
                            xref = img_info[0]
                            base_img = pdf_doc.extract_image(xref)
                            if base_img and "image" in base_img:
                                img_ext = base_img.get("ext", "png")
                                img_path = workspace_dir / f"page_{page_idx + 1}_img_{img_idx + 1}.{img_ext}"
                                img_path.write_bytes(base_img["image"])
                                try:
                                    doc.add_picture(str(img_path), width=Inches(5.5))
                                except Exception:
                                    pass
                        # If page has no text and no extracted images (e.g. vector drawing), embed page snapshot in lossless/exact mode
                        if not has_text_on_page and not img_list and preset in ("lossless", "exact"):
                            pix = page.get_pixmap(dpi=200)
                            snap_path = workspace_dir / f"page_{page_idx + 1}_render.png"
                            pix.save(str(snap_path))
                            try:
                                doc.add_picture(str(snap_path), width=Inches(6.0))
                            except Exception:
                                pass

                    if progress_callback:
                        progress_callback(JobProgress(
                            percentage=20.0 + ((page_idx + 1) / max(total_pages, 1)) * 75.0,
                            stage="Reconstructing Word Document",
                            detail=f"Page {page_idx + 1}/{total_pages}"
                        ))

                pdf_doc.close()
                doc.save(str(target_file))
        except InterruptedError:
            raise
        except Exception as e:
            if not target_file.exists():
                raise RuntimeError(f"Failed to convert PDF to DOCX: {e}")

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Saved Word (.docx) document"))

        return target_file

    def _pdf_to_image(
        self,
        source: Path,
        workspace_dir: Path,
        target_format: str,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Render PDF pages to high-resolution PNG or JPEG image using PyMuPDF."""
        import fitz

        ext = "jpeg" if target_format in ("jpg", "jpeg") else "png"
        target_file = workspace_dir / f"{source.stem}.{ext}"

        preset = str(settings.get("quality_preset", "lossless")).lower()
        default_dpi = 300 if preset in ("lossless", "exact") else 200 if preset == "high" else 150 if preset == "balanced" else 96
        dpi = int(settings.get("dpi", default_dpi))
        quality = int(settings.get("quality", 100 if preset in ("lossless", "exact") else 92))

        try:
            doc = fitz.open(str(source))
        except Exception as e:
            raise ValueError(f"Could not open PDF for rendering: {e}")

        if len(doc) == 0:
            doc.close()
            raise ValueError("PDF contains 0 pages.")

        page_images: List[Image.Image] = []
        total_pages = len(doc)
        try:
            for idx in range(total_pages):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during PDF rendering.")
                page = doc[idx]
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_images.append(img)
                if progress_callback:
                    progress_callback(JobProgress(
                        percentage=15.0 + ((idx + 1) / total_pages) * 75.0,
                        stage="Rendering PDF Pages",
                        detail=f"Page {idx + 1}/{total_pages} at {dpi} DPI"
                    ))
        finally:
            doc.close()

        if len(page_images) == 1:
            final_img = page_images[0]
        else:
            # Vertically stitch pages with a subtle separator so single output image contains all pages
            max_w = max(im.width for im in page_images)
            gap = 12
            total_h = sum(im.height for im in page_images) + gap * (len(page_images) - 1)
            final_img = Image.new("RGB", (max_w, total_h), (240, 240, 240))
            y_offset = 0
            for im in page_images:
                x_offset = (max_w - im.width) // 2
                final_img.paste(im, (x_offset, y_offset))
                y_offset += im.height + gap

        if ext == "jpeg":
            subsampling = 0 if (preset in ("lossless", "exact") or quality >= 98) else 2
            final_img.save(target_file, format="JPEG", quality=quality, subsampling=subsampling, optimize=True)
        else:
            final_img.save(target_file, format="PNG", optimize=True)

        return target_file

    def _pdf_to_html(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Convert PDF pages to structured HTML using PyMuPDF."""
        import fitz

        target_file = workspace_dir / f"{source.stem}.html"
        doc = fitz.open(str(source))
        if len(doc) == 0:
            doc.close()
            raise ValueError("PDF contains 0 pages.")

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'>",
            f"<title>{source.stem}</title>",
            "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f9fafb;color:#111827;}",
            ".page{background:#fff;padding:24px;margin-bottom:24px;border:1px solid #e5e7eb;border-radius:8px;}</style>",
            "</head><body>"
        ]
        try:
            for idx, page in enumerate(doc):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled.")
                html_parts.append(f"<div class='page' id='page-{idx+1}'>")
                html_parts.append(page.get_text("html"))
                html_parts.append("</div>")
        finally:
            doc.close()

        html_parts.append("</body></html>")
        target_file.write_text("\n".join(html_parts), encoding="utf-8")
        return target_file

    def _pdf_to_markdown(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Convert PDF text and blocks into clean Markdown."""
        import fitz

        target_file = workspace_dir / f"{source.stem}.md"
        doc = fitz.open(str(source))
        if len(doc) == 0:
            doc.close()
            raise ValueError("PDF contains 0 pages.")

        md_lines = [f"# {source.stem}\n"]
        try:
            for idx, page in enumerate(doc):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled.")
                md_lines.append(f"## Page {idx + 1}\n")
                text = page.get_text("text").strip()
                md_lines.append(text if text else "_No extractable text on this page._")
                md_lines.append("\n---\n")
        finally:
            doc.close()

        target_file.write_text("\n".join(md_lines), encoding="utf-8")
        return target_file

    def _image_to_pdf(
        self,
        image_path: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable],
        is_cancelled: Optional[Callable]
    ) -> Path:
        """Wrap image into a clean single-page or multi-page PDF with configurable DPI."""
        target_file = workspace_dir / f"{image_path.stem}.pdf"
        preset = str(settings.get("quality_preset", "lossless")).lower()
        resolution = float(settings.get("dpi", 300.0 if preset in ("lossless", "exact") else 150.0))

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
                rgb_img.save(target_file, "PDF", resolution=resolution)
            else:
                img.save(target_file, "PDF", resolution=resolution)

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

    def images_to_pdf(
        self,
        image_paths: List[Path],
        output_path: Path,
        settings: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Combine multiple images into a single multi-page PDF document (1 image per page)."""
        if not image_paths:
            raise ValueError("No images provided for PDF combination.")

        settings = settings or {}
        preset = str(settings.get("quality_preset", "lossless")).lower()
        resolution = float(settings.get("dpi", 300.0 if preset in ("lossless", "exact") else 150.0))

        total = len(image_paths)
        converted_images = []
        try:
            for idx, p in enumerate(image_paths):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during batch image-to-PDF conversion.")
                if progress_callback:
                    progress_callback(JobProgress(
                        percentage=int((idx / max(1, total)) * 80),
                        stage="Processing Images",
                        detail=f"Loading page {idx + 1}/{total}: {p.name}"
                    ))
                with Image.open(p) as img:
                    if img.mode != "RGB":
                        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "RGBA":
                            rgb_img.paste(img, mask=img.split()[3])
                        else:
                            rgb_img.paste(img.convert("RGB"))
                        converted_images.append(rgb_img)
                    else:
                        converted_images.append(img.copy())

            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled before saving PDF.")

            if progress_callback:
                progress_callback(JobProgress(percentage=85.0, stage="Saving PDF", detail=f"Writing {total} pages to {output_path.name}"))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            if converted_images:
                first = converted_images[0]
                rest = converted_images[1:]
                first.save(output_path, "PDF", resolution=resolution, save_all=True, append_images=rest)

            if progress_callback:
                progress_callback(JobProgress(percentage=100.0, stage="Complete", detail=f"Combined {total} images into multi-page PDF"))

            return output_path
        finally:
            for im in converted_images:
                im.close()

